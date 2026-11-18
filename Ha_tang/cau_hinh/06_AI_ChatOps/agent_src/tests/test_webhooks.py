import asyncio
import importlib.util
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

# Allow running webhook tests in minimal local environments without telegram/kubernetes installed.
if importlib.util.find_spec("telegram") is None:
    tg_mod = types.ModuleType("telegram")
    tg_mod.InlineKeyboardButton = MagicMock()
    tg_mod.InlineKeyboardMarkup = MagicMock()
    tg_mod.Update = MagicMock()
    tg_constants = types.ModuleType("telegram.constants")
    tg_constants.ParseMode = MagicMock()
    tg_ext = types.ModuleType("telegram.ext")
    tg_ext.Application = MagicMock()
    tg_ext.ApplicationBuilder = MagicMock()
    tg_ext.CallbackQueryHandler = MagicMock()
    tg_ext.CommandHandler = MagicMock()
    tg_ext.ContextTypes = MagicMock()
    tg_ext.MessageHandler = MagicMock()
    tg_ext.filters = MagicMock()
    sys.modules.setdefault("telegram", tg_mod)
    sys.modules.setdefault("telegram.constants", tg_constants)
    sys.modules.setdefault("telegram.ext", tg_ext)

if importlib.util.find_spec("kubernetes") is None:
    k8s_mod = types.ModuleType("kubernetes")
    k8s_client = types.ModuleType("kubernetes.client")
    k8s_config = types.ModuleType("kubernetes.config")
    k8s_rest = types.ModuleType("kubernetes.client.rest")
    k8s_rest.ApiException = Exception
    k8s_mod.client = k8s_client
    k8s_mod.config = k8s_config
    sys.modules.setdefault("kubernetes", k8s_mod)
    sys.modules.setdefault("kubernetes.client", k8s_client)
    sys.modules.setdefault("kubernetes.config", k8s_config)
    sys.modules.setdefault("kubernetes.client.rest", k8s_rest)

if importlib.util.find_spec("ruamel") is None:
    ruamel_mod = types.ModuleType("ruamel")
    ruamel_yaml = types.ModuleType("ruamel.yaml")
    ruamel_yaml.YAML = MagicMock()
    ruamel_mod.yaml = ruamel_yaml
    sys.modules.setdefault("ruamel", ruamel_mod)
    sys.modules.setdefault("ruamel.yaml", ruamel_yaml)

from app import webhooks  # noqa: E402
from app.config import Settings  # noqa: E402


@pytest.fixture()
def webhook_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    webhooks._ALERT_DEDUP_CACHE.clear()
    monkeypatch.setattr(
        webhooks,
        "settings",
        Settings(
            webhook_secret="test-webhook-secret",
            allowed_chat_id="",  # avoid background Telegram calls
            target_app_namespace="demo-app",
            argocd_app_name="web-app-gitops",
        ),
    )
    api = webhooks.create_webhook_api(bot_app=MagicMock())
    return TestClient(api)


def test_healthz(webhook_client: TestClient) -> None:
    resp = webhook_client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "kltn-chatops-agent"


def test_grafana_webhook_unconfigured_secret_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    webhooks._ALERT_DEDUP_CACHE.clear()
    monkeypatch.setattr(
        webhooks,
        "settings",
        Settings(webhook_secret="", allowed_chat_id=""),
    )
    client = TestClient(webhooks.create_webhook_api(bot_app=MagicMock()))
    resp = client.post("/webhooks/grafana", json={"status": "firing", "alerts": []})
    assert resp.status_code == 503


def test_grafana_webhook_unauthorized_returns_401(webhook_client: TestClient) -> None:
    resp = webhook_client.post("/webhooks/grafana", json={"status": "firing", "alerts": []})
    assert resp.status_code == 401

    resp_bad_header = webhook_client.post(
        "/webhooks/grafana",
        headers={"X-Webhook-Secret": "wrong-secret"},
        json={"status": "firing", "alerts": []},
    )
    assert resp_bad_header.status_code == 401

    resp_bad_bearer = webhook_client.post(
        "/webhooks/grafana",
        headers={"Authorization": "Bearer wrong-secret"},
        json={"status": "firing", "alerts": []},
    )
    assert resp_bad_bearer.status_code == 401


def test_grafana_webhook_accepts_x_webhook_secret_and_dedups(
    webhook_client: TestClient,
) -> None:
    payload = {
        "status": "firing",
        "alerts": [
            {
                "labels": {"alertname": "HighCPU", "namespace": "demo-app"},
                "annotations": {"summary": "CPU > 90%"},
            }
        ],
    }
    resp1 = webhook_client.post(
        "/webhooks/grafana",
        headers={"X-Webhook-Secret": "test-webhook-secret"},
        json=payload,
    )
    assert resp1.status_code == 202
    assert resp1.json() == {"accepted": "true", "source": "grafana"}

    resp2 = webhook_client.post(
        "/webhooks/grafana",
        headers={"X-Webhook-Secret": "test-webhook-secret"},
        json=payload,
    )
    assert resp2.status_code == 202
    assert resp2.json() == {"accepted": "true", "deduplicated": "true"}


def test_grafana_webhook_accepts_bearer_token(webhook_client: TestClient) -> None:
    payload = {
        "status": "resolved",
        "alerts": [
            {
                "labels": {"alertname": "HighMemory", "namespace": "demo-app"},
                "annotations": {"description": "Memory normalized"},
            }
        ],
    }
    resp = webhook_client.post(
        "/webhooks/grafana",
        headers={"Authorization": "Bearer test-webhook-secret"},
        json=payload,
    )
    assert resp.status_code == 202
    assert resp.json() == {"accepted": "true", "source": "grafana"}


def test_argocd_webhook_auth_and_dedup(webhook_client: TestClient) -> None:
    payload = {
        "app": "web-app-gitops",
        "sync_status": "OutOfSync",
        "health_status": "Degraded",
        "operation_phase": "Failed",
        "revision": "abcdef123456",
    }

    unauth = webhook_client.post("/webhooks/argocd", json=payload)
    assert unauth.status_code == 401

    resp1 = webhook_client.post(
        "/webhooks/argocd",
        headers={"X-Webhook-Secret": "test-webhook-secret"},
        json=payload,
    )
    assert resp1.status_code == 202
    assert resp1.json() == {"accepted": "true", "source": "argocd"}

    resp2 = webhook_client.post(
        "/webhooks/argocd",
        headers={"Authorization": "Bearer test-webhook-secret"},
        json=payload,
    )
    assert resp2.status_code == 202
    assert resp2.json() == {"accepted": "true", "deduplicated": "true"}


def test_should_suppress_duplicate_cooldown_and_expiry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    webhooks._ALERT_DEDUP_CACHE.clear()
    now = 1_000_000.0
    monkeypatch.setattr(webhooks.time, "time", lambda: now)

    assert webhooks.should_suppress_duplicate("fp-1", cooldown_sec=90.0) is False
    assert webhooks.should_suppress_duplicate("fp-1", cooldown_sec=90.0) is True
    assert webhooks.should_suppress_duplicate("fp-2", cooldown_sec=90.0) is False

    now += 95.0
    assert webhooks.should_suppress_duplicate("fp-1", cooldown_sec=90.0) is False

    now += 700.0
    assert webhooks.should_suppress_duplicate("fp-3", cooldown_sec=90.0) is False
    assert "fp-2" not in webhooks._ALERT_DEDUP_CACHE


def test_enrich_and_notify_success_and_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        webhooks,
        "settings",
        Settings(allowed_chat_id="-100123456"),
    )
    mock_collect = AsyncMock(return_value="pods: ok")
    mock_reason = AsyncMock(return_value=MagicMock(summary="ok"))
    mock_send = AsyncMock()
    monkeypatch.setattr(webhooks, "collect_full_diagnostic_bundle", mock_collect)
    monkeypatch.setattr(webhooks, "run_sre_reasoning", mock_reason)
    monkeypatch.setattr(webhooks, "send_sre_report", mock_send)

    asyncio.run(
        webhooks._enrich_and_notify(
            bot_app=MagicMock(),
            source_title="[METRIC ALERT - GRAFANA]",
            event_summary="HighCPU token=secret123",
            domain_instruction="Analyze metric alert",
        )
    )
    mock_collect.assert_awaited_once()
    mock_reason.assert_awaited_once()
    mock_send.assert_awaited_once()
    # Ensure secret was redacted before passing to LLM
    passed_telemetry = mock_reason.call_args.kwargs["telemetry_bundle"]
    assert "secret123" not in passed_telemetry

    # Error path should be caught and not raise
    monkeypatch.setattr(
        webhooks,
        "collect_full_diagnostic_bundle",
        AsyncMock(side_effect=RuntimeError("k8s unreachable")),
    )
    asyncio.run(
        webhooks._enrich_and_notify(
            bot_app=MagicMock(),
            source_title="[GITOPS EVENT - ARGO CD]",
            event_summary="OutOfSync",
            domain_instruction="Analyze sync",
        )
    )
