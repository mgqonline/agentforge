CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_approval_audit (
    approval_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    requester_user_id TEXT NOT NULL,
    approver_user_id TEXT,
    task TEXT NOT NULL,
    approval_kind TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    approval_token_hash TEXT NOT NULL,
    params JSONB NOT NULL DEFAULT '{}'::jsonb,
    decision_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    result_summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    decided_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_approval_pending
    ON agent_approval_audit (session_id, status, expires_at);

CREATE INDEX IF NOT EXISTS idx_agent_approval_status_created
    ON agent_approval_audit (status, created_at DESC);

CREATE TABLE IF NOT EXISTS agent_tool_run_audit (
    tool_run_id TEXT PRIMARY KEY,
    approval_id TEXT REFERENCES agent_approval_audit(approval_id) ON DELETE SET NULL,
    session_id TEXT NOT NULL,
    mode TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    arguments JSONB NOT NULL DEFAULT '{}'::jsonb,
    result_summary TEXT,
    status TEXT NOT NULL,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_tool_run_session
    ON agent_tool_run_audit (session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_tool_run_tool_created
    ON agent_tool_run_audit (tool_name, created_at DESC);

CREATE TABLE IF NOT EXISTS agent_users (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    roles JSONB NOT NULL DEFAULT '["operator"]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
