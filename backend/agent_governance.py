import hashlib
import json
import os
import secrets
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

import asyncpg


def _database_url() -> str:
    url = os.getenv("ASYNC_DATABASE_URL", "postgresql://aiuser:aipassword@localhost:5432/ailearning")
    return url.replace("postgresql+asyncpg://", "postgresql://", 1).replace("postgresql+psycopg://", "postgresql://", 1)


def _allow_self_approval() -> bool:
    default = "false" if os.getenv("AGENT_AUTH_REQUIRED", "false").lower() == "true" else "true"
    return os.getenv("AGENT_ALLOW_SELF_APPROVAL", default).lower() == "true"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _json(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False)


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def _dict_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


async def ensure_governance_schema() -> None:
    conn = await asyncpg.connect(_database_url())
    try:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
        migrations_dir = Path(__file__).resolve().parent / "migrations" / "versions"
        for migration_path in sorted(migrations_dir.glob("*.sql")):
            version = migration_path.stem
            applied = await conn.fetchval("SELECT 1 FROM schema_migrations WHERE version = $1", version)
            if applied:
                continue
            await conn.execute(migration_path.read_text(encoding="utf-8"))
            await conn.execute(
                "INSERT INTO schema_migrations (version) VALUES ($1) ON CONFLICT (version) DO NOTHING",
                version,
            )
    finally:
        await conn.close()


async def create_approval_request(
    session_id: str,
    requester_user_id: str,
    tenant_id: str,
    task: str,
    approval_kind: str,
    params: dict[str, Any],
    expires_seconds: int = 1800,
) -> dict[str, Any]:
    await ensure_governance_schema()
    approval_id = str(uuid.uuid4())
    approval_token = secrets.token_urlsafe(32)
    conn = await asyncpg.connect(_database_url())
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO agent_approval_audit (
                approval_id, session_id, requester_user_id, tenant_id, task, approval_kind,
                approval_token_hash, params, expires_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, now() + ($9::int * interval '1 second'))
            RETURNING approval_id, session_id, requester_user_id, tenant_id, task, approval_kind, status, created_at, expires_at
            """,
            approval_id,
            session_id,
            requester_user_id,
            tenant_id,
            task,
            approval_kind,
            _hash_token(approval_token),
            _json(params),
            expires_seconds,
        )
        result = dict(row)
        result["approval_token"] = approval_token
        result["created_at"] = _iso(result.get("created_at"))
        result["expires_at"] = _iso(result.get("expires_at"))
        return result
    finally:
        await conn.close()


async def list_pending_approvals(session_id: str, requester_user_id: str, tenant_id: str) -> list[dict[str, Any]]:
    await ensure_governance_schema()
    conn = await asyncpg.connect(_database_url())
    try:
        rows = await conn.fetch(
            """
            SELECT approval_id, session_id, requester_user_id, tenant_id, task, approval_kind, status, params, created_at, expires_at
            FROM agent_approval_audit
            WHERE session_id = $1
              AND requester_user_id = $2
              AND tenant_id = $3
              AND status = 'pending'
              AND expires_at > now()
            ORDER BY created_at ASC
            """,
            session_id,
            requester_user_id,
            tenant_id,
        )
        pending: list[dict[str, Any]] = []
        for row in rows:
            approval_token = secrets.token_urlsafe(32)
            await conn.execute(
                """
                UPDATE agent_approval_audit
                SET approval_token_hash = $2, updated_at = now()
                WHERE approval_id = $1
                """,
                row["approval_id"],
                _hash_token(approval_token),
            )
            item = dict(row)
            item["params"] = _dict_json(item.get("params"))
            item["approval_token"] = approval_token
            item["created_at"] = _iso(item.get("created_at"))
            item["expires_at"] = _iso(item.get("expires_at"))
            pending.append(item)
        return pending
    finally:
        await conn.close()


async def expire_pending_approvals() -> int:
    await ensure_governance_schema()
    conn = await asyncpg.connect(_database_url())
    try:
        result = await conn.execute(
            """
            UPDATE agent_approval_audit
            SET status = 'expired', completed_at = now(), updated_at = now()
            WHERE status = 'pending' AND expires_at <= now()
            """
        )
        return int(result.split()[-1])
    finally:
        await conn.close()


async def verify_approval_decision(
    session_id: str,
    approval_id: str,
    approval_token: str,
    approver_user_id: str,
    tenant_id: str,
    decision_payload: dict[str, Any],
) -> dict[str, Any] | None:
    if not approval_id or not approval_token:
        return None

    await ensure_governance_schema()
    conn = await asyncpg.connect(_database_url())
    try:
        row = await conn.fetchrow(
            """
            UPDATE agent_approval_audit
            SET status = 'approved',
                approver_user_id = $4,
                decision_payload = $5::jsonb,
                decided_at = now(),
                updated_at = now()
            WHERE approval_id = $1
              AND session_id = $2
              AND approval_token_hash = $3
              AND tenant_id = $6
              AND ($7::bool OR requester_user_id <> $4)
              AND status = 'pending'
              AND expires_at > now()
            RETURNING approval_id, session_id, requester_user_id, approver_user_id, tenant_id, task,
                      approval_kind, status, decision_payload, created_at, expires_at, decided_at
            """,
            approval_id,
            session_id,
            _hash_token(approval_token),
            approver_user_id,
            _json(decision_payload),
            tenant_id,
            _allow_self_approval(),
        )
        if row is None:
            return None
        result = dict(row)
        for key in ("created_at", "expires_at", "decided_at"):
            result[key] = _iso(result.get(key))
        return result
    finally:
        await conn.close()


async def reject_approval_decision(
    session_id: str,
    approval_id: str,
    approval_token: str,
    approver_user_id: str,
    tenant_id: str,
    decision_payload: dict[str, Any],
) -> bool:
    if not approval_id or not approval_token:
        return False

    await ensure_governance_schema()
    conn = await asyncpg.connect(_database_url())
    try:
        result = await conn.execute(
            """
            UPDATE agent_approval_audit
            SET status = 'rejected',
                approver_user_id = $4,
                decision_payload = $5::jsonb,
                decided_at = now(),
                completed_at = now(),
                updated_at = now()
            WHERE approval_id = $1
              AND session_id = $2
              AND approval_token_hash = $3
              AND tenant_id = $6
              AND ($7::bool OR requester_user_id <> $4)
              AND status = 'pending'
              AND expires_at > now()
            """,
            approval_id,
            session_id,
            _hash_token(approval_token),
            approver_user_id,
            _json(decision_payload),
            tenant_id,
            _allow_self_approval(),
        )
        return result.endswith("1")
    finally:
        await conn.close()


async def complete_approval(approval_id: str | None, status: str, result_summary: str) -> None:
    if not approval_id:
        return

    await ensure_governance_schema()
    conn = await asyncpg.connect(_database_url())
    try:
        await conn.execute(
            """
            UPDATE agent_approval_audit
            SET status = $2,
                result_summary = $3,
                completed_at = now(),
                updated_at = now()
            WHERE approval_id = $1 AND status = 'approved'
            """,
            approval_id,
            status,
            result_summary[:4000],
        )
    finally:
        await conn.close()


async def record_tool_run(
    session_id: str,
    requester_user_id: str,
    tenant_id: str,
    approval_id: str | None,
    mode: str,
    tool_name: str,
    arguments: Any,
    result_summary: str,
    status: str,
    duration_ms: int,
) -> None:
    await ensure_governance_schema()
    conn = await asyncpg.connect(_database_url())
    try:
        await conn.execute(
            """
            INSERT INTO agent_tool_run_audit (
                tool_run_id, approval_id, session_id, requester_user_id, tenant_id, mode, tool_name,
                arguments, result_summary, status, duration_ms
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10, $11)
            """,
            str(uuid.uuid4()),
            approval_id,
            session_id,
            requester_user_id,
            tenant_id,
            mode,
            tool_name,
            _json(arguments if isinstance(arguments, dict) else {"raw": str(arguments or "")}),
            result_summary[:4000],
            status,
            max(0, int(duration_ms)),
        )
    finally:
        await conn.close()


async def list_approval_audits(
    status: str | None = None,
    session_id: str | None = None,
    tenant_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    await expire_pending_approvals()
    conn = await asyncpg.connect(_database_url())
    try:
        rows = await conn.fetch(
            """
            SELECT approval_id, session_id, requester_user_id, approver_user_id, tenant_id, task,
                   approval_kind, status, params, decision_payload, result_summary,
                   created_at, expires_at, decided_at, completed_at, updated_at
            FROM agent_approval_audit
            WHERE ($1::text IS NULL OR status = $1)
              AND ($2::text IS NULL OR session_id = $2)
              AND ($3::text IS NULL OR tenant_id = $3)
            ORDER BY created_at DESC
            LIMIT $4
            """,
            status,
            session_id,
            tenant_id,
            max(1, min(int(limit), 200)),
        )
        results: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["params"] = _dict_json(item.get("params"))
            item["decision_payload"] = _dict_json(item.get("decision_payload"))
            for key in ("created_at", "expires_at", "decided_at", "completed_at", "updated_at"):
                item[key] = _iso(item.get(key))
            results.append(item)
        return results
    finally:
        await conn.close()


async def list_tool_run_audits(
    session_id: str | None = None,
    tool_name: str | None = None,
    tenant_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    await ensure_governance_schema()
    conn = await asyncpg.connect(_database_url())
    try:
        rows = await conn.fetch(
            """
            SELECT tool_run_id, approval_id, session_id, requester_user_id, tenant_id, mode, tool_name,
                   arguments, result_summary, status, duration_ms, created_at
            FROM agent_tool_run_audit
            WHERE ($1::text IS NULL OR session_id = $1)
              AND ($2::text IS NULL OR tool_name = $2)
              AND ($3::text IS NULL OR tenant_id = $3)
            ORDER BY created_at DESC
            LIMIT $4
            """,
            session_id,
            tool_name,
            tenant_id,
            max(1, min(int(limit), 200)),
        )
        results: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["arguments"] = _dict_json(item.get("arguments"))
            item["created_at"] = _iso(item.get("created_at"))
            results.append(item)
        return results
    finally:
        await conn.close()


async def governance_metrics(tenant_id: str | None = None) -> dict[str, Any]:
    await expire_pending_approvals()
    conn = await asyncpg.connect(_database_url())
    try:
        approval_rows = await conn.fetch(
            """
            SELECT status, count(*) AS count
            FROM agent_approval_audit
            WHERE ($1::text IS NULL OR tenant_id = $1)
            GROUP BY status
            """,
            tenant_id,
        )
        tool_rows = await conn.fetch(
            """
            SELECT tool_name, status, count(*) AS count, coalesce(avg(duration_ms), 0)::int AS avg_duration_ms
            FROM agent_tool_run_audit
            WHERE ($1::text IS NULL OR tenant_id = $1)
            GROUP BY tool_name, status
            ORDER BY count DESC
            """,
            tenant_id,
        )
        return {
            "approvals": {row["status"]: row["count"] for row in approval_rows},
            "tool_runs": [
                {
                    "tool_name": row["tool_name"],
                    "status": row["status"],
                    "count": row["count"],
                    "avg_duration_ms": row["avg_duration_ms"],
                }
                for row in tool_rows
            ],
        }
    finally:
        await conn.close()
