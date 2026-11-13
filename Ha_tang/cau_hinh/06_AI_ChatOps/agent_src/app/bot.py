import html
import logging
import re

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.config import settings
from app.llm_engine import SREResponse, classify_intent, run_sre_reasoning
from app.security import (
    audit_store,
    check_telegram_authorization,
    evaluate_deterministic_guardrail,
)
from app.tools import (
    collect_full_diagnostic_bundle,
    get_argocd_app_status,
    get_cluster_overview,
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


async def send_sre_report(
    bot_app: Application,
    chat_id: int | str,
    title: str,
    sre_resp: SREResponse,
) -> None:
    severity_badge = {
        "INFO": "INFO",
        "WARNING": "WARNING",
        "CRITICAL": "CRITICAL",
    }.get(sre_resp.severity, "INFO")

    formatted_analysis = _markdown_to_telegram_html(sre_resp.analysis_markdown)
    body = (
        f"<b>{_safe_html(title)}</b> [{severity_badge}]\n"
        f"<i>Engine: {_safe_html(sre_resp.provider_used)}</i>\n\n"
        f"{formatted_analysis}"
    )
    await bot_app.bot.send_message(
        chat_id=chat_id,
        text=body[:4000],
        parse_mode=ParseMode.HTML,
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
        "🤖 <b>KLTN AI ChatOps SRE Agent (v1.0 — Read-Only &amp; RCA)</b>\n\n"
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
    await update.message.reply_text(await get_cluster_overview())


async def cmd_pods(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard_update(update):
        return
    assert update.message is not None
    await update.message.reply_text(await inspect_app_pods())


async def cmd_metrics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard_update(update):
        return
    assert update.message is not None
    await update.message.reply_text(await query_sli_metrics())


async def cmd_gitops(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard_update(update):
        return
    assert update.message is not None
    await update.message.reply_text(await get_argocd_app_status())


async def cmd_audit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard_update(update):
        return
    assert update.message is not None
    audit_text = audit_store.format_recent_audits()
    await update.message.reply_text(f"📜 *Nhật ký Kiểm duyệt Bảo mật:*\n\n{audit_text}")


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
        await update.message.reply_text(
            f"🛡️ <b>[Zero-Trust Policy Gate — Đã chặn tự động]</b>\n"
            f"• Lý do: {_safe_html(static_reason)}\n"
            f"• Sự kiện này đã được ghi nhận vào `/audit`.",
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
        await status_msg.edit_text(
            f"🛡️ <b>[AI Safety Guardrail — Đã chặn tự động]</b>\n"
            f"• Lý do: {_safe_html(reason)}",
            parse_mode=ParseMode.HTML,
        )
        return

    if decision.intent == "CLUSTER_OVERVIEW":
        await status_msg.edit_text(await get_cluster_overview())
        return
    if decision.intent == "APP_PODS_STATUS":
        await status_msg.edit_text(await inspect_app_pods())
        return
    if decision.intent == "ARGOCD_STATUS":
        await status_msg.edit_text(await get_argocd_app_status())
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
        title="🧠 Kết quả Phân tích & Chẩn đoán Sự cố",
        sre_resp=sre_resp,
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
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_natural_message))
    return app
