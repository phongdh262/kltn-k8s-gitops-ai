import os
from dataclasses import dataclass, field


def _parse_csv_set(raw: str) -> set[str]:
    return {item.strip() for item in raw.split(",") if item.strip()}


@dataclass(frozen=True)
class Settings:
    # Telegram Configuration
    telegram_bot_token: str = field(
        default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", "").strip(), repr=False
    )
    allowed_chat_id: str = field(default_factory=lambda: os.getenv("ALLOWED_CHAT_ID", "").strip())
    allowed_user_ids: set[str] = field(
        default_factory=lambda: _parse_csv_set(os.getenv("ALLOWED_USER_IDS", ""))
    )

    # Multi-Provider AI Gateway (Gemini Primary + Groq Failover)
    gemini_api_key: str = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", "").strip(), repr=False
    )
    gemini_router_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_ROUTER_MODEL", "gemini-flash-lite-latest")
    )
    gemini_reasoning_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_REASONING_MODEL", "gemini-flash-lite-latest")
    )
    groq_api_key: str = field(
        default_factory=lambda: os.getenv("GROQ_API_KEY", "").strip(), repr=False
    )
    groq_fallback_model: str = field(
        default_factory=lambda: os.getenv("GROQ_FALLBACK_MODEL", "openai/gpt-oss-20b")
    )

    # Cluster & Monitoring Targets (via WireGuard wg0)
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

    # GitOps GitHub Integration (Deterministic YAML Mutation)
    github_token: str = field(
        default_factory=lambda: os.getenv("GITHUB_TOKEN", "").strip(), repr=False
    )
    github_repo: str = field(
        default_factory=lambda: os.getenv("GITHUB_REPO", "phongdh262/kltn-k8s-gitops-ai").strip()
    )
    github_branch: str = field(
        default_factory=lambda: os.getenv("GITHUB_BRANCH", "main").strip()
    )
    gitops_manifest_path: str = field(
        default_factory=lambda: os.getenv(
            "GITOPS_MANIFEST_PATH",
            "Ha_tang/cau_hinh/05_ArgoCD_GitOps/manifests/web-app.yaml",
        ).strip()
    )

    # Internal Webhook & Proactive K8s Watcher Settings
    webhook_port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    webhook_secret: str = field(
        default_factory=lambda: os.getenv("WEBHOOK_SECRET", "").strip(), repr=False
    )
    enable_k8s_watcher: bool = field(
        default_factory=lambda: os.getenv("ENABLE_K8S_WATCHER", "true").lower() == "true"
    )
    action_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("ACTION_TTL_SECONDS", "300"))
    )

    def validate_security(self) -> None:
        """Dừng khởi động khi thiếu cấu hình truy cập; không in giá trị bí mật."""
        required = {
            "TELEGRAM_BOT_TOKEN": self.telegram_bot_token,
            "ALLOWED_CHAT_ID": self.allowed_chat_id,
            "WEBHOOK_SECRET": self.webhook_secret,
        }
        invalid = [
            name
            for name, value in required.items()
            if not value or (value.startswith("<") and value.endswith(">"))
        ]
        if not self.allowed_user_ids or any(
            not user_id.isascii() or not user_id.isdecimal() or int(user_id) <= 0
            for user_id in self.allowed_user_ids
        ):
            invalid.append("ALLOWED_USER_IDS")
        chat_digits = self.allowed_chat_id.removeprefix("-")
        if not chat_digits.isascii() or not chat_digits.isdecimal() or int(chat_digits) == 0:
            invalid.append("ALLOWED_CHAT_ID")
        if invalid:
            names = ", ".join(sorted(set(invalid)))
            raise ValueError(f"Cấu hình bảo mật thiếu hoặc không hợp lệ: {names}")


settings = Settings()
