import unittest
import os
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from main import app
from agent_security import create_dev_token

class TestAuditEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Token for admin / approver / operator (contains audit:read permission)
        self.authorized_token = create_dev_token(
            user_id="test-audit-user",
            roles=["operator", "approver"],
            tenant_id="default"
        )
        # Token with viewer role (only has chat:use, lacks audit:read)
        self.unauthorized_token = create_dev_token(
            user_id="test-viewer-user",
            roles=["viewer"],
            tenant_id="default"
        )

    def test_audit_approvals_unauthorized(self):
        """测试无 audit:read 权限访问审批审计列表被拒绝 (403)"""
        res = self.client.get(
            "/api/agent/audit/approvals",
            headers={"Authorization": f"Bearer {self.unauthorized_token}"}
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("missing permission", res.json().get("detail", ""))

    def test_audit_approvals_authorized(self):
        """测试带 audit:read 权限正常获取审批审计列表 (200)"""
        res = self.client.get(
            "/api/agent/audit/approvals?limit=5",
            headers={"Authorization": f"Bearer {self.authorized_token}"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("items", res.json())

    def test_audit_tool_runs_authorized(self):
        """测试带 audit:read 权限获取工具运行日志 (200)"""
        res = self.client.get(
            "/api/agent/audit/tool-runs?limit=5",
            headers={"Authorization": f"Bearer {self.authorized_token}"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("items", res.json())

    def test_governance_metrics_authorized(self):
        """测试治理指标汇总接口 (200)"""
        res = self.client.get(
            "/api/agent/metrics/governance",
            headers={"Authorization": f"Bearer {self.authorized_token}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("approvals", data)
        self.assertIn("tool_runs", data)

    def test_active_tasks_authorized(self):
        """测试活跃任务接口 (200)"""
        res = self.client.get(
            "/api/agent/tasks/active",
            headers={"Authorization": f"Bearer {self.authorized_token}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("max_active_tasks", data)
        self.assertIn("items", data)

if __name__ == "__main__":
    unittest.main()
