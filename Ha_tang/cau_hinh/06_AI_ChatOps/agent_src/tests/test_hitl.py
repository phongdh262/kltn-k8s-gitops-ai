import pytest

from app import security
from app.config import Settings


@pytest.fixture()
def gov_store(monkeypatch: pytest.MonkeyPatch) -> security.ActionGovernanceStore:
    monkeypatch.setattr(
        security,
        "settings",
        Settings(allowed_chat_id="-100123", allowed_user_ids={"1001", "1002"}),
    )
    return security.ActionGovernanceStore(ttl_seconds=300, max_audit_entries=10)


@pytest.mark.parametrize("replicas", [1, 2, 3, 5])
def test_validate_replica_bounds_valid(replicas: int) -> None:
    assert security.validate_replica_bounds(replicas) == replicas


@pytest.mark.parametrize("replicas", [0, -1, 6, 100])
def test_validate_replica_bounds_invalid(replicas: int) -> None:
    with pytest.raises(ValueError):
        security.validate_replica_bounds(replicas)


def test_create_proposal_replica_validation(gov_store: security.ActionGovernanceStore) -> None:
    proposal = gov_store.create_proposal(
        action_type="gitops_scale",
        summary="Scale web-app to 3 replicas",
        params={"app": "web-app", "namespace": "demo-app", "replicas": 3},
    )
    assert len(proposal.action_id) == 10
    assert proposal.params["replicas"] == 3

    with pytest.raises(ValueError):
        gov_store.create_proposal(
            action_type="gitops_scale",
            summary="Missing replicas",
            params={"app": "web-app"},
        )

    with pytest.raises(ValueError):
        gov_store.create_proposal(
            action_type="gitops_scale",
            summary="Out of bounds",
            params={"app": "web-app", "replicas": 8},
        )


def test_pop_valid_proposal_single_use_and_auth(
    gov_store: security.ActionGovernanceStore,
) -> None:
    proposal = gov_store.create_proposal(
        action_type="rollout_restart",
        summary="Restart web-app",
        params={"deployment": "web-app", "namespace": "demo-app"},
    )

    # Unauthorized user cannot pop and does NOT consume the proposal
    assert gov_store.pop_valid_proposal(proposal.action_id, user_id="9999") is None

    # Authorized user pops once
    popped = gov_store.pop_valid_proposal(proposal.action_id, user_id="1001")
    assert popped is not None
    assert popped.action_id == proposal.action_id

    # Single-use: second pop returns None
    assert gov_store.pop_valid_proposal(proposal.action_id, user_id="1001") is None


def test_discard_proposal_auth_and_single_use(
    gov_store: security.ActionGovernanceStore,
) -> None:
    proposal = gov_store.create_proposal(
        action_type="argocd_sync",
        summary="Sync web-app-gitops",
        params={"app": "web-app-gitops"},
    )

    assert gov_store.discard_proposal(proposal.action_id, user_id="9999") is None

    discarded = gov_store.discard_proposal(proposal.action_id, user_id="1002")
    assert discarded is not None
    assert discarded.action_id == proposal.action_id

    assert gov_store.pop_valid_proposal(proposal.action_id, user_id="1002") is None


def test_proposal_ttl_expiry(
    gov_store: security.ActionGovernanceStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = security.time.time()
    monkeypatch.setattr(security.time, "time", lambda: now)

    proposal = gov_store.create_proposal(
        action_type="rollout_restart",
        summary="Restart web-app",
        params={"deployment": "web-app"},
    )

    now = proposal.created_at + 301.0
    assert gov_store.pop_valid_proposal(proposal.action_id, user_id="1001") is None


def test_governance_audit_log_redacts_secrets(
    gov_store: security.ActionGovernanceStore,
) -> None:
    assert "Chưa có thao tác" in gov_store.format_recent_audits()
    gov_store.record_audit(
        actor="1001",
        action_type="gitops_scale",
        summary="Scale web-app token=supersecret",
        status="APPROVED",
        detail="password=dbpass",
    )
    rendered = gov_store.format_recent_audits()
    assert "APPROVED" in rendered
    assert "supersecret" not in rendered
    assert "dbpass" not in rendered
