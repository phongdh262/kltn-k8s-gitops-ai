import hmac
import json
import logging
import time
from typing import Any

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from telegram.ext import Application

from app.bot import send_sre_report
from app.config import settings
from app.llm_engine import run_sre_reasoning
from app.security import redact_sensitive_text
from app.tools import collect_full_diagnostic_bundle

logger = logging.getLogger(__name__)

_ALERT_DEDUP_CACHE: dict[str, float] = {}


def should_suppress_duplicate(fingerprint: str, cooldown_sec: float = 90.0) -> bool:
    """Kiểm tra khóa sự kiện (fingerprint) trong cửa sổ thời gian để tránh gửi trùng cảnh báo."""
    now = time.time()
    expired = [k for k, ts in _ALERT_DEDUP_CACHE.items() if now - ts > 600.0]
    for k in expired:
        _ALERT_DEDUP_CACHE.pop(k, None)

    last_ts = _ALERT_DEDUP_CACHE.get(fingerprint, 0.0)
    if now - last_ts < cooldown_sec:
        logger.info("Suppressed duplicate event")
        return True

    _ALERT_DEDUP_CACHE[fingerprint] = now
    return False


def _verify_webhook_secret(
    x_webhook_secret: str | None,
    authorization: str | None,
) -> None:
    if not settings.webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook authentication is not configured")

    token = (x_webhook_secret or "").strip()
    if not token and authorization:
        parts = authorization.strip().split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip()

    if not token or not hmac.compare_digest(
        token.encode("utf-8"), settings.webhook_secret.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


async def _enrich_and_notify(
    bot_app: Application,
    source_title: str,
    event_summary: str,
    domain_instruction: str,
) -> None:
    if not settings.allowed_chat_id:
        logger.warning("ALLOWED_CHAT_ID is empty; skipping proactive Telegram alert.")
        return
    try:
        telemetry = await collect_full_diagnostic_bundle()
        sre_resp = await run_sre_reasoning(
            telemetry_bundle=(
                f"{telemetry}\n\n=== [UNTRUSTED WEBHOOK EVENT] ===\n"
                f"{redact_sensitive_text(event_summary, max_chars=3000)}"
            ),
            trigger_prompt=(
                f"Nguồn cảnh báo chủ động: {source_title}\n"
                f"Yêu cầu phân tích: {domain_instruction}"
            ),
        )
        await send_sre_report(
            bot_app=bot_app,
            chat_id=settings.allowed_chat_id,
            title=source_title,
            sre_resp=sre_resp,
        )
    except Exception as exc:
        logger.error("Error while processing proactive webhook alert (%s)", type(exc).__name__)


def create_webhook_api(bot_app: Application) -> FastAPI:
    api = FastAPI(
        title="ChatOps Internal Webhook API",
        version="1.1.0",
        docs_url=None,
        redoc_url=None,
    )

    @api.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "kltn-chatops-agent", "version": "1.1.0"}

    @api.post("/webhooks/grafana", status_code=202)
    async def grafana_webhook(
        request: Request,
        background_tasks: BackgroundTasks,
        x_webhook_secret: str | None = Header(default=None),
        authorization: str | None = Header(default=None),
    ) -> dict[str, str]:
        _verify_webhook_secret(x_webhook_secret, authorization)
        payload: dict[str, Any] = await request.json()
        state = str(payload.get("status", "firing")).upper()
        alerts = payload.get("alerts", [])

        summaries: list[str] = []
        alert_names: list[str] = []
        for al in alerts[:5]:
            labels = al.get("labels", {})
            ann = al.get("annotations", {})
            alert_name = labels.get("alertname", "GrafanaMetricAlert")
            namespace = labels.get("namespace", settings.target_app_namespace)
            alert_names.append(f"{alert_name}:{namespace}:{state}")
            summary = ann.get("summary") or ann.get("description") or json.dumps(labels)
            summaries.append(
                f"- Alert: {alert_name} | Trạng thái: {state} | Namespace: {namespace} | Mô tả: {summary}"
            )

        fingerprint = "grafana:" + ",".join(sorted(set(alert_names or [state])))
        if should_suppress_duplicate(fingerprint, cooldown_sec=90.0):
            return {"accepted": "true", "deduplicated": "true"}

        summary_text = redact_sensitive_text(
            "\n".join(summaries) or json.dumps(payload, ensure_ascii=False), max_chars=3000
        )
        logger.info(
            "Accepted Grafana Metric Alert (%s): %s", redact_sensitive_text(state), summary_text
        )

        background_tasks.add_task(
            _enrich_and_notify,
            bot_app,
            redact_sensitive_text(f"[METRIC ALERT - GRAFANA] ({state})"),
            summary_text,
            (
                "Đây là cảnh báo vượt ngưỡng chỉ số tài nguyên/SLI từ Grafana Unified Alerting. "
                "Hãy đối chiếu với số liệu PromQL thực tế, đánh giá mức độ ảnh hưởng tài nguyên và đề xuất hướng xử lý."
            ),
        )
        return {"accepted": "true", "source": "grafana"}

    @api.post("/webhooks/argocd", status_code=202)
    async def argocd_webhook(
        request: Request,
        background_tasks: BackgroundTasks,
        x_webhook_secret: str | None = Header(default=None),
        authorization: str | None = Header(default=None),
    ) -> dict[str, str]:
        _verify_webhook_secret(x_webhook_secret, authorization)
        payload: dict[str, Any] = await request.json()

        app_name = str(payload.get("app", settings.argocd_app_name))
        sync_status = str(payload.get("sync_status", "Unknown"))
        health_status = str(payload.get("health_status", "Unknown"))
        revision = str(payload.get("revision", ""))[:7]
        op_phase = str(payload.get("operation_phase", "Unknown"))

        fingerprint = f"argocd:{app_name}:{sync_status}:{op_phase}:{revision}"
        if should_suppress_duplicate(fingerprint, cooldown_sec=90.0):
            return {"accepted": "true", "deduplicated": "true"}

        event_text = (
            f"- Application: {app_name}\n"
            f"- Sync Status: {sync_status}\n"
            f"- Operation Phase: {op_phase}\n"
            f"- Health Status: {health_status}\n"
            f"- Git Revision: {revision or 'N/A'}"
        )
        event_text = redact_sensitive_text(event_text, max_chars=3000)
        logger.info("Accepted Argo CD GitOps Event: %s", event_text.replace("\n", " | "))

        background_tasks.add_task(
            _enrich_and_notify,
            bot_app,
            redact_sensitive_text(f"[GITOPS EVENT - ARGO CD] ({sync_status})"),
            event_text,
            (
                "Đây là sự kiện trạng thái đồng bộ cấu hình từ Argo CD Notifications. "
                "Hãy kiểm tra nguyên nhân sai lệch cấu hình (OutOfSync/SyncFailed) giữa Git repository và cụm K3s."
            ),
        )
        return {"accepted": "true", "source": "argocd"}

    return api

