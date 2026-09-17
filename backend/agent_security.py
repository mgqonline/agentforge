import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Any

import asyncpg

DEFAULT_AUTH_SECRET = "dev-agent-auth-secret"
_WS_TICKETS: dict[str, dict[str, Any]] = {}


ROLE_PERMISSIONS: dict[str, set[str]] = {
    "viewer": {"chat:use"},
    # operator：可查看工具运行日志、活跃任务（审计只读），不可审批
    "operator": {"chat:use", "tool:read", "audit:read"},
    # approver：在 operator 基础上增加审批决策权 + 审批记录查看
    "approver": {"chat:use", "tool:read", "audit:read", "approval:decide"},
    # admin：全权限，额外拥有策略覆盖能力
    "admin": {"chat:use", "tool:read", "approval:decide", "audit:read", "policy:override"},
}


@dataclass(frozen=True)
class AuthContext:
    user_id: str
    roles: tuple[str, ...]
    session_id: str
    tenant_id: str = "default"

    @property
    def permissions(self) -> set[str]:
        granted: set[str] = set()
        for role in self.roles:
            granted.update(ROLE_PERMISSIONS.get(role, set()))
        return granted

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions


def _auth_secret() -> str:
    return os.getenv("AGENT_AUTH_SECRET", os.getenv("APP_SECRET", DEFAULT_AUTH_SECRET))


def _auth_required() -> bool:
    return os.getenv("AGENT_AUTH_REQUIRED", "false").lower() == "true"


def _runtime_env() -> str:
    return os.getenv("AGENT_ENV", os.getenv("APP_ENV", os.getenv("ENV", "development"))).lower()


def validate_security_config() -> None:
    """Fail fast on auth settings that are unsafe outside local development."""
    production_like = _runtime_env() in {"prod", "production", "stage", "staging"}
    if production_like and not _auth_required():
        raise RuntimeError("AGENT_AUTH_REQUIRED must be true in production-like environments")
    if _auth_required() and _auth_secret() == DEFAULT_AUTH_SECRET:
        raise RuntimeError("AGENT_AUTH_SECRET or APP_SECRET must be set when AGENT_AUTH_REQUIRED=true")
    if production_like and os.getenv("AGENT_ALLOW_DEV_AUTH", "false").lower() == "true":
        raise RuntimeError("AGENT_ALLOW_DEV_AUTH must not be enabled in production-like environments")


def _database_url() -> str:
    url = os.getenv("ASYNC_DATABASE_URL", "postgresql://aiuser:aipassword@localhost:5432/ailearning")
    return url.replace("postgresql+asyncpg://", "postgresql://", 1).replace("postgresql+psycopg://", "postgresql://", 1)


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("utf-8"))


def _decode_signed_token(token: str) -> dict[str, Any] | None:
    parts = token.split(".")
    if len(parts) != 2:
        return None
    payload_b64, signature_b64 = parts
    expected = hmac.new(_auth_secret().encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    try:
        supplied = _b64url_decode(signature_b64)
    except Exception:
        return None
    if not hmac.compare_digest(expected, supplied):
        return None
    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    exp = payload.get("exp")
    if exp is not None and int(exp) < int(time.time()):
        return None
    return payload if isinstance(payload, dict) else None


def _create_signed_token(payload: dict[str, Any]) -> str:
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("utf-8").rstrip("=")
    signature = hmac.new(_auth_secret().encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    return f"{payload_b64}.{signature_b64}"


def create_dev_token(user_id: str, roles: list[str] | None = None, ttl_seconds: int = 86400, tenant_id: str = "default") -> str:
    payload = {
        "sub": user_id,
        "roles": roles or ["admin"],
        "tenant_id": tenant_id,
        "exp": int(time.time()) + ttl_seconds,
    }
    return _create_signed_token(payload)


def create_context_token(auth: AuthContext, ttl_seconds: int = 120) -> str:
    return create_dev_token(
        auth.user_id,
        roles=list(auth.roles),
        ttl_seconds=ttl_seconds,
        tenant_id=auth.tenant_id,
    )


def create_ws_ticket(auth: AuthContext, session_id: str, ttl_seconds: int = 60) -> str:
    ticket = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + max(10, min(int(ttl_seconds), 300))
    _WS_TICKETS[ticket] = {
        "sub": auth.user_id,
        "roles": list(auth.roles),
        "tenant_id": auth.tenant_id,
        "session_id": session_id,
        "exp": expires_at,
    }
    return ticket


def consume_ws_ticket(ticket: str | None, session_id: str) -> AuthContext | None:
    if not ticket:
        return None
    payload = _WS_TICKETS.pop(ticket, None)
    if not payload:
        return None
    if int(payload.get("exp") or 0) < int(time.time()):
        return None
    if str(payload.get("session_id") or "") != session_id:
        return None
    roles = tuple(str(role) for role in payload.get("roles") or [] if str(role) in ROLE_PERMISSIONS)
    return AuthContext(
        user_id=str(payload.get("sub") or "anonymous"),
        roles=roles,
        session_id=session_id,
        tenant_id=str(payload.get("tenant_id") or "default"),
    )


def _hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return base64.urlsafe_b64encode(digest).decode("utf-8")


def _valid_username(username: str) -> bool:
    return 3 <= len(username) <= 64 and all(ch.isalnum() or ch in "._-@" for ch in username)


async def register_user(username: str, password: str, roles: list[str] | None = None) -> dict[str, Any]:
    username = username.strip().lower()
    if not _valid_username(username):
        raise ValueError("username must be 3-64 characters and only contain letters, numbers, . _ - @")
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")

    from agent_governance import ensure_governance_schema

    await ensure_governance_schema()
    conn = await asyncpg.connect(_database_url())
    try:
        existing_count = await conn.fetchval("SELECT count(*) FROM agent_users")
        requested_roles = roles if roles else (["admin"] if int(existing_count or 0) == 0 else ["operator", "approver"])
        safe_roles = [role for role in requested_roles if role in ROLE_PERMISSIONS]
        if not safe_roles:
            safe_roles = ["operator"]
        user_id = str(uuid.uuid4())
        salt = base64.urlsafe_b64encode(os.urandom(18)).decode("utf-8")
        password_hash = _hash_password(password, salt)
        row = await conn.fetchrow(
            """
            INSERT INTO agent_users (user_id, username, password_hash, password_salt, roles)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            RETURNING user_id, username, roles, created_at
            """,
            user_id,
            username,
            password_hash,
            salt,
            json.dumps(safe_roles),
        )
        return dict(row)
    except asyncpg.UniqueViolationError as exc:
        raise ValueError("username already exists") from exc
    finally:
        await conn.close()


async def login_user(username: str, password: str) -> dict[str, Any] | None:
    from agent_governance import ensure_governance_schema

    await ensure_governance_schema()
    conn = await asyncpg.connect(_database_url())
    try:
        row = await conn.fetchrow(
            """
            SELECT user_id, username, password_hash, password_salt, roles
            FROM agent_users
            WHERE username = $1
            """,
            username.strip().lower(),
        )
        if row is None:
            return None
        expected = _hash_password(password, row["password_salt"])
        if not hmac.compare_digest(expected, row["password_hash"]):
            return None
        roles = row["roles"]
        if isinstance(roles, str):
            roles = json.loads(roles)
        token = create_dev_token(row["user_id"], [str(role) for role in roles])
        return {
            "token": token,
            "user": {
                "user_id": row["user_id"],
                "username": row["username"],
                "roles": roles,
                "permissions": sorted(AuthContext(row["user_id"], tuple(roles), "http").permissions),
            },
        }
    finally:
        await conn.close()


def authenticate(token: str | None, session_id: str, fallback_user_id: str | None = None) -> AuthContext:
    payload = _decode_signed_token(token or "") if token else None
    if payload:
        roles_raw = payload.get("roles") or []
        roles = tuple(str(role) for role in roles_raw if str(role) in ROLE_PERMISSIONS)
        return AuthContext(
            user_id=str(payload.get("sub") or fallback_user_id or "anonymous"),
            roles=roles or ("viewer",),
            session_id=session_id,
            tenant_id=str(payload.get("tenant_id") or "default"),
        )

    if _auth_required():
        return AuthContext(user_id="anonymous", roles=(), session_id=session_id)

    if os.getenv("AGENT_ALLOW_DEV_AUTH", "true").lower() != "true":
        return AuthContext(user_id="anonymous", roles=(), session_id=session_id)

    dev_roles = tuple(role.strip() for role in os.getenv("AGENT_DEV_ROLES", "admin").split(",") if role.strip())
    return AuthContext(
        user_id=fallback_user_id or os.getenv("AGENT_DEV_USER_ID", "dev-admin"),
        roles=dev_roles or ("admin",),
        session_id=session_id,
    )


def require_permission(auth: AuthContext, permission: str) -> None:
    if not auth.has_permission(permission):
        raise PermissionError(f"missing permission: {permission}")


def auth_to_dict(auth: AuthContext) -> dict[str, Any]:
    return {
        "user_id": auth.user_id,
        "roles": list(auth.roles),
        "session_id": auth.session_id,
        "tenant_id": auth.tenant_id,
        "permissions": sorted(auth.permissions),
    }
