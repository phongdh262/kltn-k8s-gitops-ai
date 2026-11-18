import html
import logging
import re
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.config import settings
from app.llm_engine import SREResponse, classify_intent, run_sre_reasoning
from app.security import (
    PendingAction,
    audit_store,
    check_telegram_authorization,
    evaluate_deterministic_guardrail,
    governance_store,
)
from app.tools import (
    collect_full_diagnostic_bundle,
    execute_argocd_refresh_sync,
    execute_gitops_manifest_mutation,
    execute_rollout_restart,
    get_argocd_app_status,
    get_cluster_overview,
    get_deployment_replicas,
    inspect_app_pods,
    query_sli_metrics,
)

logger = logging.getLogger(__name__)


def _safe_html(text: str) -> str:
    return html.escape(text)


def _markdown_to_telegram_html(text: str) -> str:
    """Chuyển đổi các thẻ Markdown cơ bản (**bold**, `code`, ###) sang HTML chuẩn của Telegram."""
    escaped = html.escape(text.strip())
    escaped = re.sub(r"^#{1,4}\s*(.+)$", r"<b>\1</b>", escaped, flags=re.MULTILINE)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"^\s*-\s+", "• ", escaped, flags=re.MULTILINE)
    return escaped


def build_proposal_keyboard(proposal: PendingAction) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=f"✅ Duyệt: {proposal.summary[:36]}",
                    callback_data=f"approve:{proposal.action_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Hủy bỏ",
                    callback_data=f"reject:{proposal.action_id}",
                ),
            ]
        ]
    )


def register_proposal_from_ai(
    sre_resp: SREResponse, current_replicas: int | None = None
) -> PendingAction | None:
    prop = sre_resp.proposal
    if prop.action_type == "none":
        return None

    params: dict[str, Any] = {}
    if prop.action_type == "gitops_scale":
        if prop.replicas is None:
            return None
        params = {
            "app": settings.target_deployment_name,
            "namespace": settings.target_app_namespace,
            "old_replicas": current_replicas,
            "replicas": prop.replicas,
        }
        summary = prop.summary or (
            f"GitOps Scale {settings.target_deployment_name} -> {prop.replicas} replicas"
        )
    elif prop.action_type == "gitops_image":
        if not prop.image:
            return None
        params = {
            "app": settings.target_deployment_name,
            "namespace": settings.target_app_namespace,
            "image": prop.image,
        }
        summary = prop.summary or f"GitOps Image {settings.target_deployment_name} -> {prop.image}"
    elif prop.action_type == "argocd_sync":
        params = {
            "app": settings.argocd_app_name,
            "namespace": settings.argocd_namespace,
        }
        summary = prop.summary or f"Argo CD Hard Refresh ({settings.argocd_app_name})"
    elif prop.action_type == "rollout_restart":
        params = {
            "app": settings.target_deployment_name,
            "namespace": settings.target_app_namespace,
        }
        summary = prop.summary or f"Rollout Restart {settings.target_deployment_name}"
    else:
        return None

    try:
        return governance_store.create_proposal(
            action_type=prop.action_type,
            summary=summary,
            params=params,
        )
    except ValueError as exc:
        logger.warning("Rejected out-of-bounds proposal (%s): %s", prop.action_type, exc)
        return None


def _format_proposal_params(proposal: PendingAction) -> str:
    p = proposal.params
    app = p.get("app", settings.target_deployment_name)
    ns = p.get("namespace", settings.target_app_namespace)
    lines = [
        f"• Thao tác: <code>{_safe_html(proposal.action_type)}</code>",
        f"• App / Namespace: <code>{_safe_html(str(app))}</code> / <code>{_safe_html(str(ns))}</code>",
    ]
    if proposal.action_type == "gitops_scale":
        old_rep = p.get("old_replicas")
        new_rep = p.get("replicas")
        old_label = str(old_rep) if old_rep is not None else "?"
        lines.append(f"• Replicas: <code>{_safe_html(old_label)} -&gt; {_safe_html(str(new_rep))}</code>")
    elif proposal.action_type == "gitops_image":
        lines.append(f"• Image: <code>{_safe_html(str(p.get('image', '')))}</code>")
    lines.append(f"• Chi tiết: {_safe_html(proposal.summary)}")
    return "\n".join(lines)


async def send_sre_report(
    bot_app: Application,
    chat_id: int | str,
    title: str,
    sre_resp: SREResponse,
    extra_proposal: PendingAction | None = None,
) -> None:
    severity_badge = {
        "INFO": "INFO",
        "WARNING": "WARNING",
        "CRITICAL": "CRITICAL",
    }.get(sre_resp.severity, "INFO")

    current_replicas: int | None = None
    if not extra_proposal and sre_resp.proposal.action_type == "gitops_scale":
        current_replicas = await get_deployment_replicas()

    proposal = extra_proposal or register_proposal_from_ai(sre_resp, current_replicas=current_replicas)
    formatted_analysis = _markdown_to_telegram_html(sre_resp.analysis_markdown)
    body = (
        f"<b>{_safe_html(title)}</b> [{severity_badge}]\n"
        f"<i>Engine: {_safe_html(sre_resp.provider_used)}</i>\n\n"
        f"{formatted_analysis}"
    )

    reply_markup = None
    if proposal:
        ttl_mins = max(1, settings.action_ttl_seconds // 60)
        body += (
            f"\n\n🔐 <b>Đề xuất khắc phục (HITL — hiệu lực {ttl_mins} phút):</b>\n"
            f"{_format_proposal_params(proposal)}"
        )
        reply_markup = build_proposal_keyboard(proposal)

    await bot_app.bot.send_message(
        chat_id=chat_id,
        text=body[:4000],
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
    )


async def _guard_update(update: Update) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    if not chat:
        return False
    allowed, reason = check_telegram_authorization(chat.id, user.id if user else None)
    if not allowed:
        if update.effective_message:
            await update.effective_message.reply_text(f"⛔ Truy cập bị từ chối: {reason}")
        return False
    return True


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard_update(update):
        return
    help_text = (
        "🤖 <b>KLTN AI ChatOps SRE Agent (v1.2 — HITL &amp; GitOps)</b>\n\n"
        "<b>Lệnh tra cứu trực tiếp (Bypass LLM &lt; 300ms):</b>\n"
        "• /status — Sức khỏe 3 VPS (WireGuard + CPU/RAM/Disk từ Prometheus)\n"
        "• /pods — Phân bổ &amp; trạng thái các Pod ứng dụng\n"
        "• /metrics — Chỉ số SLI Container &amp; PostgreSQL\n"
        "• /gitops — Trạng thái đồng bộ Argo CD Application\n"
        "• /audit — Nhật ký kiểm duyệt bảo mật\n\n"
        "💬 <b>Hỗ trợ Tiếng Việt tự nhiên:</b>\n"
        "Gõ câu hỏi bất kỳ (VD: <i>\"Kiểm tra log tại sao web-app vừa bị restart\"</i>)."
    )
    assert update.message is not None
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard_update(update):
        return
    assert update.message is not None
    text = _markdown_to_telegram_html(await get_cluster_overview())
    await update.message.reply_text(text[:4000], parse_mode=ParseMode.HTML)


async def cmd_pods(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard_update(update):
        return
    assert update.message is not None
    text = _markdown_to_telegram_html(await inspect_app_pods())
    await update.message.reply_text(text[:4000], parse_mode=ParseMode.HTML)


async def cmd_metrics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard_update(update):
        return
    assert update.message is not None
    text = _markdown_to_telegram_html(await query_sli_metrics())
    await update.message.reply_text(text[:4000], parse_mode=ParseMode.HTML)


async def cmd_gitops(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard_update(update):
        return
    assert update.message is not None
    text = _markdown_to_telegram_html(await get_argocd_app_status())
    await update.message.reply_text(text[:4000], parse_mode=ParseMode.HTML)


async def cmd_audit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard_update(update):
        return
    assert update.message is not None
    audit_text = governance_store.format_recent_audits()
    text = _markdown_to_telegram_html(f"**[AUDIT LOG]**\n\n{audit_text}")
    await update.message.reply_text(text[:4000], parse_mode=ParseMode.HTML)


async def handle_natural_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard_update(update):
        return
    assert update.message is not None and update.effective_chat is not None
    user_text = (update.message.text or "").strip()
    if not user_text:
        return

    actor = (
        update.effective_user.username or str(update.effective_user.id)
        if update.effective_user
        else "admin"
    )

    # Lớp 1: Kiểm duyệt bằng luật tĩnh tức thời (< 1ms)
    is_safe_static, static_reason = evaluate_deterministic_guardrail(user_text)
    if not is_safe_static:
        audit_store.record_audit(
            actor=actor,
            event_type="BLOCKED_STATIC_POLICY",
            summary=user_text[:80],
            status="BLOCKED",
            detail=static_reason,
        )
        governance_store.record_audit(
            actor=actor,
            action_type="BLOCKED_STATIC_POLICY",
            summary=user_text[:80],
            status="BLOCKED",
            detail=static_reason,
        )
        await update.message.reply_text(
            f"🛡️ <b>[Zero-Trust Policy Gate — Đã chặn tự động]</b>\n"
            f"• Lý do: {_safe_html(static_reason)}\n"
            f"• Sự kiện này đã được ghi nhận vào <code>/audit</code>.",
            parse_mode=ParseMode.HTML,
        )
        return

    status_msg = await update.message.reply_text("🔍 Đang phân tích yêu cầu...")

    decision = await classify_intent(user_text)
    if not decision.is_safe or decision.intent == "UNSAFE_BLOCKED":
        reason = decision.safety_reason or "Phát hiện yêu cầu có rủi ro xâm phạm an toàn cụm K3s."
        audit_store.record_audit(
            actor=actor,
            event_type="BLOCKED_AI_GUARDRAIL",
            summary=user_text[:80],
            status="BLOCKED",
            detail=reason,
        )
        governance_store.record_audit(
            actor=actor,
            action_type="BLOCKED_AI_GUARDRAIL",
            summary=user_text[:80],
            status="BLOCKED",
            detail=reason,
        )
        await status_msg.edit_text(
            f"🛡️ <b>[AI Safety Guardrail — Đã chặn tự động]</b>\n"
            f"• Lý do: {_safe_html(reason)}",
            parse_mode=ParseMode.HTML,
        )
        return

    if decision.intent == "CLUSTER_OVERVIEW":
        text = _markdown_to_telegram_html(await get_cluster_overview())
        await status_msg.edit_text(text[:4000], parse_mode=ParseMode.HTML)
        return
    if decision.intent == "APP_PODS_STATUS":
        text = _markdown_to_telegram_html(await inspect_app_pods())
        await status_msg.edit_text(text[:4000], parse_mode=ParseMode.HTML)
        return
    if decision.intent == "ARGOCD_STATUS":
        text = _markdown_to_telegram_html(await get_argocd_app_status())
        await status_msg.edit_text(text[:4000], parse_mode=ParseMode.HTML)
        return

    await status_msg.edit_text(
        "📡 Đang thu thập Logs (hiện tại & phiên crash), K8s Events, PromQL Metrics & Argo CD..."
    )
    telemetry = await collect_full_diagnostic_bundle()

    await status_msg.edit_text("🧠 AI SRE đang phân tích nguyên nhân gốc rễ (RCA)...")
    sre_resp = await run_sre_reasoning(telemetry, user_text)

    await status_msg.delete()
    await send_sre_report(
        bot_app=context.application,
        chat_id=update.effective_chat.id,
        title="Kết quả Phân tích & Chẩn đoán Sự cố",
        sre_resp=sre_resp,
    )


# ==============================================================================
# 3. HUMAN-IN-THE-LOOP (HITL) CALLBACK APPROVAL HANDLER
# ==============================================================================
async def handle_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    chat = update.effective_chat
    user = update.effective_user
    allowed, reason = check_telegram_authorization(
        chat.id if chat else "", user.id if user else None
    )
    if not allowed:
        actor_unauth = (user.username or str(user.id)) if user else "unknown"
        governance_store.record_audit(
            actor=actor_unauth,
            action_type="UNAUTHORIZED_CALLBACK",
            summary=query.data[:80],
            status="REJECTED",
            detail=reason,
        )
        await query.answer(f"⛔ Không có quyền: {reason}", show_alert=True)
        return

    actor = (user.username or str(user.id)) if user else "admin"
    user_id = user.id if user else None
    decision_cmd, _, action_id = query.data.partition(":")

    if decision_cmd in ("reject", "cancel"):
        discarded = governance_store.discard_proposal(action_id, user_id=user_id)
        if discarded:
            governance_store.record_audit(
                actor=actor,
                action_type=discarded.action_type,
                summary=discarded.summary,
                status="REJECTED",
            )
        await query.answer("Đã hủy bỏ thao tác.")
        await query.edit_message_reply_markup(reply_markup=None)
        if query.message:
            await query.message.reply_text(
                f"❌ Quản trị viên <code>{_safe_html(actor)}</code> đã hủy bỏ đề xuất <code>{_safe_html(action_id)}</code>.",
                parse_mode=ParseMode.HTML,
            )
        return

    if decision_cmd != "approve":
        await query.answer("Lệnh không hợp lệ.")
        return

    proposal = governance_store.pop_valid_proposal(action_id, user_id=user_id)
    if not proposal:
        await query.answer("⏱ Đề xuất đã hết hạn hoặc đã được xử lý!", show_alert=True)
        await query.edit_message_reply_markup(reply_markup=None)
        return

    await query.answer("⚙️ Đang thực thi hành động đã phê duyệt...")
    await query.edit_message_reply_markup(reply_markup=None)

    try:
        if proposal.action_type == "rollout_restart":
            result_msg = await execute_rollout_restart(
                namespace=proposal.params.get("namespace"),
                deployment_name=proposal.params.get("app"),
            )
            status_header = "✅ <b>Rolling Restart đã được kích hoạt</b>"
        elif proposal.action_type == "argocd_sync":
            result_msg = await execute_argocd_refresh_sync(
                app_name=proposal.params.get("app"),
            )
            status_header = "✅ <b>Argo CD hard refresh triggered</b>"
        elif proposal.action_type == "gitops_scale":
            result_msg = await execute_gitops_manifest_mutation(
                replicas=int(proposal.params["replicas"]),
                reason=f"Approved by {actor}",
            )
            status_header = "✅ <b>Git commit created</b>"
        elif proposal.action_type == "gitops_image":
            result_msg = await execute_gitops_manifest_mutation(
                image=str(proposal.params["image"]),
                reason=f"Approved by {actor}",
            )
            status_header = "✅ <b>Git commit created</b>"
        else:
            raise ValueError(f"Unsupported action_type: {proposal.action_type}")

        governance_store.record_audit(
            actor=actor,
            action_type=proposal.action_type,
            summary=proposal.summary,
            status="EXECUTED",
            detail=result_msg,
        )
        if query.message:
            await query.message.reply_text(
                f"{status_header}\n"
                f"• Người phê duyệt: <code>{_safe_html(actor)}</code>\n"
                f"• Kết quả: {_safe_html(result_msg)}",
                parse_mode=ParseMode.HTML,
            )
    except Exception as exc:
        logger.exception("Failed executing approved action %s", proposal.action_id)
        governance_store.record_audit(
            actor=actor,
            action_type=proposal.action_type,
            summary=proposal.summary,
            status="FAILED",
            detail=str(exc),
        )
        if query.message:
            await query.message.reply_text(
                f"⚠️ <b>Thực thi thất bại:</b> <code>{_safe_html(str(exc))}</code>",
                parse_mode=ParseMode.HTML,
            )


def build_telegram_application() -> Application:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN chưa được cấu hình!")

    app = ApplicationBuilder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler(["start", "help"], cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("pods", cmd_pods))
    app.add_handler(CommandHandler("metrics", cmd_metrics))
    app.add_handler(CommandHandler("gitops", cmd_gitops))
    app.add_handler(CommandHandler("audit", cmd_audit))
    app.add_handler(CallbackQueryHandler(handle_action_callback))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_natural_message))
    return app
