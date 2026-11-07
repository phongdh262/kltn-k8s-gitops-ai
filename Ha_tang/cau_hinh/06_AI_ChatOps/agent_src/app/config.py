import os
from dataclasses import dataclass, field


def _parse_csv_set(raw: str) -> set[str]:
    return {item.strip() for item in raw.split(",") if item.strip()}


@dataclass(frozen=True)
class Settings:
    # Telegram Configuration (v1.0 — Outbound Async Long-Polling)
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    allowed_chat_id: str = field(default_factory=lambda: os.getenv("ALLOWED_CHAT_ID", "").strip())
    allowed_user_ids: set[str] = field(
        default_factory=lambda: _parse_csv_set(os.getenv("ALLOWED_USER_IDS", ""))
    )

    # Multi-Provider AI Gateway (Gemini Primary + Groq Auto-Failover)
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_router_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_ROUTER_MODEL", "gemini-flash-lite-latest")
    )
    gemini_reasoning_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_REASONING_MODEL", "gemini-flash-lite-latest")
    )
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    groq_fallback_model: str = field(
        default_factory=lambda: os.getenv("GROQ_FALLBACK_MODEL", "openai/gpt-oss-20b")
    )

    # Cluster & Monitoring Read-Only Targets (via WireGuard wg0)
    target_app_namespace: str = field(
        default_factory=lambda: os.getenv("TARGET_APP_NAMESPACE", "demo-app")
    )
    target_deployment_name: str = field(
        default_factory=lambda: os.getenv("TARGET_DEPLOYMENT_NAME", "web-app")
    )
    argocd_namespace: str = field(
        default_factory=lambda: os.getenv("ARGOCD_NAMESPACE", "argocd")
    )
    argocd_app_name: str = field(
        default_factory=lambda: os.getenv("ARGOCD_APP_NAME", "web-app-gitops")
    )
    prometheus_url: str = field(
        default_factory=lambda: os.getenv(
            "PROMETHEUS_URL",
            "http://monitoring-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090",
        )
    )
    health_port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))


settings = Settings()
