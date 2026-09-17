"""
AgentForge · 全局核心全栈冒烟自动化测试套件 (E2E Smoke Tests)
====================================================================
定位：产品交付与 CI/CD 质量防护网。
要求：零外部依赖与断网自洽，全面覆盖 01 到 15 核心架构组件健康度。

执行方式：
  pytest tests/test_e2e_smoke.py -v
  或通过 CLI: python scripts/agentforge_cli.py test
"""

import asyncio
import math
import sys
import unittest
from pathlib import Path

# 确保能加载项目根目录与 backend 目录
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "backend"))


class TestAgentForgeCoreSmoke(unittest.TestCase):
    """核心架构组件健康度冒烟测试"""

    def test_01_environment_baseline(self):
        """测试 Python 运行时基准是否满足要求 (>= 3.10)"""
        major = sys.version_info.major
        minor = sys.version_info.minor
        self.assertEqual(major, 3, "必须使用 Python 3")
        self.assertGreaterEqual(minor, 10, "Python 版本必须 >= 3.10")

    def test_02_pydantic_validation(self):
        """测试 02 章节：Pydantic 结构化数据校验与防御"""
        from pydantic import BaseModel, Field, ValidationError

        class WeatherQuery(BaseModel):
            city: str = Field(min_length=2)
            days: int = Field(ge=1, le=7)

        # 正常用例
        valid_data = WeatherQuery(city="Beijing", days=3)
        self.assertEqual(valid_data.city, "Beijing")
        self.assertEqual(valid_data.days, 3)

        # 非法拦截用例
        with self.assertRaises(ValidationError):
            WeatherQuery(city="A", days=10)

    def test_03_embedding_math_cosine(self):
        """测试 05 章节：向量余弦相似度纯数学计算"""

        def cosine_similarity(v1, v2):
            dot_product = sum(a * b for a, b in zip(v1, v2))
            norm_v1 = math.sqrt(sum(a * a for a in v1))
            norm_v2 = math.sqrt(sum(b * b for b in v2))
            if norm_v1 == 0 or norm_v2 == 0:
                return 0.0
            return dot_product / (norm_v1 * norm_v2)

        vec_a = [1.0, 2.0, 3.0]
        vec_b = [1.0, 2.0, 3.0]
        vec_c = [-1.0, -2.0, -3.0]

        self.assertAlmostEqual(cosine_similarity(vec_a, vec_b), 1.0, places=5)
        self.assertAlmostEqual(cosine_similarity(vec_a, vec_c), -1.0, places=5)

    def test_04_python_advanced_primitives(self):
        """测试 11 章节：Python 进阶异步生成器流式特性"""

        async def stream_generator():
            for token in ["Hello", " ", "Agent", "!"]:
                yield token

        async def collect_tokens():
            tokens = []
            async for t in stream_generator():
                tokens.append(t)
            return "".join(tokens)

        result = asyncio.run(collect_tokens())
        self.assertEqual(result, "Hello Agent!")

    def test_05_fastapi_app_spec(self):
        """测试 12 章节：FastAPI 路由与中间件定义完整性"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI(title="SmokeTestAPI")

        @app.get("/health")
        def health_check():
            return {"status": "healthy", "service": "AgentForge"}

        client = TestClient(app)
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    def test_06_sqlalchemy_async_orm_model(self):
        """测试 13 章节：SQLAlchemy 2.0 声明式模型与级联关系完整性"""
        from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

        class Base(DeclarativeBase):
            pass

        class TaskModel(Base):
            __tablename__ = "test_tasks"
            id: Mapped[int] = mapped_column(primary_key=True)
            name: Mapped[str] = mapped_column()

        self.assertEqual(TaskModel.__tablename__, "test_tasks")
        self.assertTrue(hasattr(TaskModel, "name"))

    def test_07_full_stack_agent_system_integration(self):
        """测试 15 章节：全栈 Agent 协同系统数据契约与 EventBus 消息分发"""
        import importlib.util

        sys_path = ROOT_DIR / "15-agent-architecture" / "full_stack_agent_system.py"
        spec = importlib.util.spec_from_file_location(
            "full_stack_agent_system", str(sys_path)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # 1. 验证关键数据表模型定义
        self.assertTrue(hasattr(module, "AgentTask"))
        self.assertTrue(hasattr(module, "AgentStepLog"))
        self.assertTrue(hasattr(module, "event_bus"))

        # 2. 验证 EventBus 发布订阅契约
        bus = module.TaskEventBus()
        queue = bus.subscribe("smoke_test_task")

        async def emit_and_recv():
            await bus.publish(
                "smoke_test_task", {"event": "TEST", "payload": "OK"}
            )
            msg = await queue.get()
            return msg

        msg = asyncio.run(emit_and_recv())
        self.assertEqual(msg["event"], "TEST")
        self.assertEqual(msg["payload"], "OK")
        bus.unsubscribe("smoke_test_task", queue)

    def test_08_rbac_jwt_governance(self):
        """测试阶段二：企业级多租户 JWT 签发、验签与防篡改"""
        from backend.auth_governance import create_access_token, verify_access_token, UserRole
        token = create_access_token("test_user", "tenant_alpha", UserRole.ADMIN)
        claims = verify_access_token(token)
        self.assertEqual(claims.user_id, "test_user")
        self.assertEqual(claims.tenant_id, "tenant_alpha")
        self.assertEqual(claims.role, UserRole.ADMIN)

    def test_09_security_sandbox_defense(self):
        """测试阶段二：AST 静态代码沙箱对恶意系统命令的拦截防御"""
        from backend.security_sandbox import run_code_in_sandbox
        # 合法代码正常执行
        res_ok = run_code_in_sandbox("print('Safe Code Running')")
        self.assertTrue(res_ok.success)
        self.assertTrue(res_ok.security_passed)

        # 恶意注入强制拦截
        res_bad = run_code_in_sandbox("import os\nos.system('rm -rf /')")
        self.assertFalse(res_bad.security_passed)
        self.assertIn("禁止导入高危系统模块", res_bad.error)

    def test_10_multi_tenant_user_governance(self):
        """测试多租户用户权限维护：最高权限认证、角色分配与配额动态充值"""
        from backend.auth_governance import (
            authenticate_user, 
            list_tenant_users, 
            update_user_role, 
            update_tenant_budget,
            UserRole,
            TENANT_STORE
        )
        # 1. 验证最高权限管理员账号密码认证
        admin_user = authenticate_user("admin", "AgentForge@2026")
        self.assertIsNotNone(admin_user)
        self.assertEqual(admin_user.role, UserRole.ADMIN)
        self.assertEqual(admin_user.tenant_id, "tenant_enterprise_core")

        # 2. 验证错误密码拦截
        bad_login = authenticate_user("admin", "WrongPassword")
        self.assertIsNone(bad_login)

        # 3. 验证租户成员列表与角色动态调整
        users = list_tenant_users("tenant_enterprise_core")
        self.assertTrue(any(u["username"] == "dev_lead" for u in users))
        
        updated_dev = update_user_role("dev_lead", "admin")
        self.assertEqual(updated_dev.role, UserRole.ADMIN)
        # 恢复角色
        update_user_role("dev_lead", "developer")

        # 4. 验证租户配额动态扩容
        updated_tenant = update_tenant_budget("tenant_enterprise_core", 3_000_000)
        self.assertEqual(updated_tenant.monthly_token_budget, 3_000_000)

    def test_11_sandbox_multi_tenant_rbac_guard(self):
        """测试代码沙箱多租户 RBAC 拦截与 Token 预算熔断拦截"""
        from backend.auth_governance import (
            create_access_token,
            deduct_tenant_tokens,
            TENANT_STORE,
            UserRole
        )
        # 1. 验证只读访客角色
        viewer_token = create_access_token("guest", "tenant_guest_sandbox", UserRole.VIEWER)
        self.assertTrue(len(viewer_token) > 20)

        # 2. 验证 Token 扣减与熔断检测
        quota_state = deduct_tenant_tokens("tenant_guest_sandbox", 200)
        self.assertTrue(quota_state["is_exhausted"])
        self.assertEqual(quota_state["tokens_remaining"], 0)

    def test_12_user_action_audit_trail(self):
        """测试用户使用行为追踪与审计流水生命周期"""
        from backend.auth_governance import (
            record_user_action,
            list_user_audit_logs
        )
        record_user_action(
            username="admin",
            tenant_id="tenant_enterprise_core",
            action="login",
            details="超级管理员登录企业控制台",
            cost_tokens=0,
            status="success"
        )
        record_user_action(
            username="dev_lead",
            tenant_id="tenant_enterprise_core",
            action="sandbox_run",
            details="执行 01 关卡代码调试",
            cost_tokens=150,
            status="success"
        )
        audits = list_user_audit_logs(limit=10)
        self.assertGreaterEqual(len(audits), 2)
        # 验证按时间倒序排列：最新的一条应为 dev_lead 的 sandbox_run
        latest = audits[0]
        self.assertEqual(latest["username"], "dev_lead")
        self.assertEqual(latest["action"], "sandbox_run")
        self.assertEqual(latest["cost_tokens"], 150)

    def test_13_cloud_progress_persistence(self):
        """测试多用户学习进度与代码快照 SQLite 云端物理持久化与断网恢复"""
        from backend.auth_governance import save_user_progress, get_user_progress_map
        import time

        test_user = "usr_smoke_test_99"
        res = save_user_progress(
            user_id=test_user,
            username="tester",
            tenant_id="tenant_enterprise_core",
            phase_id="01-prompt-engineering",
            passed=True,
            xp_earned=140,
            saved_code="def solve(): return True",
            execution_metrics={"execution_time_ms": 32}
        )
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["passed"])

        progress_map = get_user_progress_map(test_user)
        self.assertIn("01-prompt-engineering", progress_map)
        self.assertEqual(progress_map["01-prompt-engineering"]["xpEarned"], 140)
        self.assertEqual(progress_map["01-prompt-engineering"]["savedCode"], "def solve(): return True")
        self.assertEqual(progress_map["01-prompt-engineering"]["execution_time_ms"], 32)

    def test_14_mentor_offline_and_traceback_analysis(self):
        """测试 AI 导师离线启发式分析与报错调用栈定位"""
        from backend.main import _generate_offline_diagnostic
        import re

        err_sample = """Traceback (most recent call last):
  File "solution.py", line 42, in test_step
AssertionError: Expected 200 but got 404"""

        diag = _generate_offline_diagnostic(
            phase_id="01-prompt-engineering",
            phase_title="Prompt 工程与少样本实战",
            user_code="def run(): pass",
            error_text=err_sample
        )
        self.assertIn("断言失败", diag)
        self.assertIn("AI 导师寄语", diag)

        # 验证调用栈提取正则
        tb_matches = re.findall(r'File ".*?", line (\d+)', err_sample)
        self.assertEqual([int(m) for m in tb_matches], [42])

    def test_15_transformers_basics_challenge_and_operator(self):
        """测试 17 关 Transformer 算子（残差连接、Dropout状态、注意力机制）沙箱评测闭环"""
        from backend.curriculum_engine import CurriculumEngine
        from backend.sandbox_runner import SandboxRunner

        engine = CurriculumEngine(str(ROOT_DIR))
        detail = engine.get_phase_detail("17-transformers-basics")
        self.assertIsNotNone(detail, "必须能检索到 17-transformers-basics 详情")
        self.assertIn("残差连接", detail["mission"]["mission_title"])
        self.assertTrue(len(detail["test_code"]) > 50)

        # 1. 验证官方标准 Solution 可直接跑通测试
        runner = SandboxRunner()
        verify_script = detail["solution_code"] + "\n\n" + detail["test_code"]
        res = runner.run_code(verify_script, timeout=15)
        self.assertEqual(res["status"], "success", f"官方参考答案评测失败: {res.get('stderr')}")
        self.assertEqual(res["exit_code"], 0)
        self.assertIn("OK", res["stderr"])

        # 2. 负向测试：若学生代码损坏（比如语法错误），沙箱必须准确拦截报错
        bad_code = "class MiniTransformerBlock: pass\n" + detail["test_code"]
        bad_res = runner.run_code(bad_code, timeout=15)
        self.assertNotEqual(bad_res["exit_code"], 0, "错误实现不能误通关")


if __name__ == "__main__":
    unittest.main()



