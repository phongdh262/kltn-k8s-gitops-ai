from dataclasses import replace

import pytest

from app import security
from app.config import Settings, _parse_csv_set


def test_parse_csv_set() -> None:
    assert _parse_csv_set(" 111, 222 , , 333 ") == {"111", "222", "333"}
    assert _parse_csv_set("") == set()


def test_settings_repr_hides_secrets() -> None:
    cfg = Settings(
        telegram_bot_token="tg-secret-value",
        allowed_chat_id="-100123456",
        allowed_user_ids={"123456"},
        gemini_api_key="gem-secret-value",
        groq_api_key="groq-secret-value",
        github_token="gh-secret-value",
        webhook_secret="wh-secret-value",
    )
    rendered = repr(cfg)
    for secret in (
        "tg-secret-value",
        "gem-secret-value",
        "groq-secret-value",
        "gh-secret-value",
        "wh-secret-value",
    ):
        assert secret not in rendered


def test_validate_security_accepts_valid_config() -> None:
    cfg = Settings(
        telegram_bot_token="valid-bot-token",
        allowed_chat_id="-100123456789",
        allowed_user_ids={"111111", "222222"},
        webhook_secret="valid-webhook-secret",
    )
    cfg.validate_security()


@pytest.mark.parametrize(
    ("overrides", "expected_field"),
    [
        ({"telegram_bot_token": ""}, "TELEGRAM_BOT_TOKEN"),
        ({"telegram_bot_token": "<REPLACE_ME>"}, "TELEGRAM_BOT_TOKEN"),
        ({"webhook_secret": ""}, "WEBHOOK_SECRET"),
        ({"webhook_secret": "<SECRET>"}, "WEBHOOK_SECRET"),
        ({"allowed_chat_id": ""}, "ALLOWED_CHAT_ID"),
        ({"allowed_chat_id": "0"}, "ALLOWED_CHAT_ID"),
        ({"allowed_chat_id": "not-a-number"}, "ALLOWED_CHAT_ID"),
        ({"allowed_user_ids": set()}, "ALLOWED_USER_IDS"),
        ({"allowed_user_ids": {"0"}}, "ALLOWED_USER_IDS"),
        ({"allowed_user_ids": {"abc"}}, "ALLOWED_USER_IDS"),
    ],
)
def test_validate_security_fail_closed(overrides: dict, expected_field: str) -> None:
    base = Settings(
        telegram_bot_token="valid-bot-token",
        allowed_chat_id="123456789",
        allowed_user_ids={"123456"},
        webhook_secret="valid-webhook-secret",
    )
    bad_cfg = replace(base, **overrides)
    with pytest.raises(ValueError) as exc_info:
        bad_cfg.validate_security()
    assert expected_field in str(exc_info.value)


def test_check_telegram_authorization(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        security,
        "settings",
        Settings(allowed_chat_id="-100999", allowed_user_ids={"1001", "1002"}),
    )

    ok, msg = security.check_telegram_authorization(-100999, 1001)
    assert ok is True
    assert msg == "OK"

    ok, _ = security.check_telegram_authorization("-100888", 1001)
    assert ok is False

    ok, _ = security.check_telegram_authorization(-100999, 9999)
    assert ok is False

    ok, _ = security.check_telegram_authorization(-100999, None)
    assert ok is False


def test_check_telegram_authorization_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        security,
        "settings",
        Settings(allowed_chat_id="", allowed_user_ids=set()),
    )
    ok, _ = security.check_telegram_authorization(123, 456)
    assert ok is False


def test_redact_sensitive_text_patterns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        security,
        "settings",
        Settings(
            telegram_bot_token="custom-tg-secret-999",
            gemini_api_key="custom-gem-secret-999",
            groq_api_key="custom-groq-secret-999",
            webhook_secret="custom-wh-secret-999",
            github_token="custom-gh-secret-999",
        ),
    )

    tg_tok = "12345678:" + "A" * 34
    gh_tok = "ghp_" + "B" * 32
    gem_tok = "AIza" + "C" * 35
    groq_tok = "gsk_" + "D" * 40
    priv_key = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA\n-----END RSA PRIVATE KEY-----"

    raw = (
        f'{{"password": "my-db-pass", "api_key": "inline-key-123"}} '
        f"Authorization: Bearer abc.def.ghi "
        f"postgres=postgresql://admin:superpass@db.internal:5432/app "
        f"email=ops.team@example.com "
        f"tg={tg_tok} gh={gh_tok} gem={gem_tok} groq={groq_tok} "
        f"cfg=custom-gh-secret-999 {priv_key}"
    )

    redacted = security.redact_sensitive_text(raw, max_chars=None)

    for leaked in (
        "my-db-pass",
        "inline-key-123",
        "abc.def.ghi",
        "superpass",
        "ops.team@example.com",
        tg_tok,
        gh_tok,
        gem_tok,
        groq_tok,
        "custom-gh-secret-999",
        "MIIEowIBAAKCAQEA",
    ):
        assert leaked not in redacted

    assert "[REDACTED_PRIVATE_KEY]" in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "Bearer [REDACTED]" in redacted


def test_redact_sensitive_text_empty_and_truncation() -> None:
    assert security.redact_sensitive_text("") == ""
    long_text = "x" * 100 + "tail-end"
    truncated = security.redact_sensitive_text(long_text, max_chars=20)
    assert len(truncated) == 20
    assert truncated.endswith("tail-end")


def test_deterministic_guardrail_and_telemetry_wrapper() -> None:
    safe, _ = security.evaluate_deterministic_guardrail("kiểm tra pod web-app")
    assert safe is True

    blocked, reason = security.evaluate_deterministic_guardrail("kubectl delete pod web-app")
    assert blocked is False
    assert reason

    wrapped = security.wrap_untrusted_telemetry("token=supersecretvalue")
    assert "<untrusted_cluster_telemetry>" in wrapped
    assert "supersecretvalue" not in wrapped


def test_security_audit_store() -> None:
    store = security.SecurityAuditStore(max_entries=5)
    assert "Chưa có sự kiện" in store.format_recent_audits()
    store.record_audit("1001", "BLOCKED", "password=secret123", "DENIED", detail="token=abc")
    output = store.format_recent_audits()
    assert "BLOCKED" in output
    assert "secret123" not in output
    assert "abc" not in output
