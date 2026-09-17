import os

from agent_policy import evaluate_approval_decision, evaluate_task_policy, evaluate_tool_policy
from agent_security import (
    AuthContext,
    authenticate,
    consume_ws_ticket,
    create_dev_token,
    create_ws_ticket,
    validate_security_config,
)


def test_signed_token_authenticates_roles():
    os.environ["AGENT_AUTH_SECRET"] = "unit-test-secret"
    token = create_dev_token("approver-1", ["approver"])

    auth = authenticate(token, "session-1")

    assert auth.user_id == "approver-1"
    assert auth.has_permission("approval:decide")
    assert auth.has_permission("tool:read")


def test_auth_required_rejects_missing_token():
    os.environ["AGENT_AUTH_REQUIRED"] = "true"
    try:
        auth = authenticate(None, "session-1")
        assert auth.roles == ()
        assert not auth.has_permission("chat:use")
    finally:
        os.environ.pop("AGENT_AUTH_REQUIRED", None)


def test_ws_ticket_is_session_bound_and_single_use():
    auth = AuthContext("operator-1", ("operator",), "session-1", tenant_id="tenant-a")
    ticket = create_ws_ticket(auth, "session-1", ttl_seconds=30)

    consumed = consume_ws_ticket(ticket, "session-1")
    reused = consume_ws_ticket(ticket, "session-1")
    wrong_session = consume_ws_ticket(create_ws_ticket(auth, "session-1", ttl_seconds=30), "session-2")

    assert consumed is not None
    assert consumed.user_id == "operator-1"
    assert consumed.tenant_id == "tenant-a"
    assert reused is None
    assert wrong_session is None


def test_auth_required_rejects_default_secret_config():
    previous_required = os.environ.get("AGENT_AUTH_REQUIRED")
    previous_secret = os.environ.get("AGENT_AUTH_SECRET")
    previous_app_secret = os.environ.get("APP_SECRET")
    os.environ["AGENT_AUTH_REQUIRED"] = "true"
    os.environ.pop("AGENT_AUTH_SECRET", None)
    os.environ.pop("APP_SECRET", None)
    try:
        try:
            validate_security_config()
            assert False, "expected validate_security_config to reject default auth secret"
        except RuntimeError as exc:
            assert "AGENT_AUTH_SECRET" in str(exc)
    finally:
        if previous_required is None:
            os.environ.pop("AGENT_AUTH_REQUIRED", None)
        else:
            os.environ["AGENT_AUTH_REQUIRED"] = previous_required
        if previous_secret is None:
            os.environ.pop("AGENT_AUTH_SECRET", None)
        else:
            os.environ["AGENT_AUTH_SECRET"] = previous_secret
        if previous_app_secret is None:
            os.environ.pop("APP_SECRET", None)
        else:
            os.environ["APP_SECRET"] = previous_app_secret


def test_sql_write_intent_is_blocked_by_policy():
    decision = evaluate_tool_policy("query_sql_database", {"query": "delete from users"}, {"tool:read"})

    assert not decision.allowed
    assert decision.risk_level == "critical"


def test_readonly_sql_requires_tool_permission():
    denied = evaluate_tool_policy("query_sql_database", {"query": "show tables"}, set())
    allowed = evaluate_tool_policy("query_sql_database", {"query": "show tables"}, {"tool:read"})

    assert not denied.allowed
    assert allowed.allowed


def test_orchestrator_side_effect_requires_approval():
    decision = evaluate_task_policy("请删除旧数据", "orchestrator", {"chat:use"})

    assert decision.allowed
    assert decision.requires_approval
    assert decision.approval_kind == "side_effect"


def test_approval_decision_requires_permission():
    denied = evaluate_approval_decision({"chat:use"})
    allowed = evaluate_approval_decision({"approval:decide"})

    assert not denied.allowed
    assert allowed.allowed


if __name__ == "__main__":
    test_signed_token_authenticates_roles()
    test_auth_required_rejects_missing_token()
    test_ws_ticket_is_session_bound_and_single_use()
    test_auth_required_rejects_default_secret_config()
    test_sql_write_intent_is_blocked_by_policy()
    test_readonly_sql_requires_tool_permission()
    test_orchestrator_side_effect_requires_approval()
    test_approval_decision_requires_permission()
    print("agent security policy tests passed")
