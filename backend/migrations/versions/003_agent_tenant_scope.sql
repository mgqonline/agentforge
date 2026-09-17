ALTER TABLE agent_approval_audit
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default';

ALTER TABLE agent_tool_run_audit
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default';

ALTER TABLE agent_tool_run_audit
    ADD COLUMN IF NOT EXISTS requester_user_id TEXT;

CREATE INDEX IF NOT EXISTS idx_agent_approval_pending_scope
    ON agent_approval_audit (tenant_id, requester_user_id, session_id, status, expires_at);

CREATE INDEX IF NOT EXISTS idx_agent_tool_run_scope
    ON agent_tool_run_audit (tenant_id, requester_user_id, session_id, created_at DESC);
