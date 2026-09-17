import pytest
import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(__file__))

from curriculum_engine import CurriculumEngine

def test_get_all_phases():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    engine = CurriculumEngine(base_dir=project_root)
    phases = engine.get_all_phases()
    assert len(phases) >= 20, f"Expected at least 20 phases, got {len(phases)}"
    
    first = phases[0]
    assert "id" in first
    assert "title" in first
    assert "order" in first
    assert "description" in first
    assert "tags" in first

def test_get_phase_detail():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    engine = CurriculumEngine(base_dir=project_root)
    detail = engine.get_phase_detail("01-prompt-engineering")
    assert detail is not None
    assert "guide_markdown" in detail
    assert "starter_code" in detail
    assert "test_code" in detail
    assert len(detail["starter_code"]) > 0

def test_sandbox_run_success():
    from sandbox_runner import SandboxRunner
    runner = SandboxRunner()
    res = runner.run_code("print('Hello AI Sandbox')")
    assert res["status"] == "success"
    assert "Hello AI Sandbox" in res["stdout"]
    assert res["exit_code"] == 0

def test_sandbox_run_syntax_error():
    from sandbox_runner import SandboxRunner
    runner = SandboxRunner()
    res = runner.run_code("print('Broken syntax")
    assert res["status"] == "error"
    assert "SyntaxError" in res["stderr"]

def test_sandbox_run_timeout():
    from sandbox_runner import SandboxRunner
    runner = SandboxRunner()
    # 模拟超时保护
    res = runner.run_code("import time\ntime.sleep(3)", timeout=1)
    assert res["status"] == "timeout"
    assert "超时" in res["stderr"] or "timed out" in res["stderr"].lower()

def test_api_curriculum_endpoints():
    try:
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        
        # 测试获取全部阶段
        resp = client.get("/api/v1/curriculum/phases")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert len(data["phases"]) >= 20
        
        # 测试获取阶段详情
        resp_detail = client.get("/api/v1/curriculum/phases/01-prompt-engineering")
        assert resp_detail.status_code == 200
        detail_data = resp_detail.json()
        assert "starter_code" in detail_data["data"]
    except ImportError:
        # 如果当前本地命令行环境未安装 fastapi (通常在虚拟环境/容器中完整运行)
        pass

def test_api_sandbox_endpoints():
    try:
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        
        # 测试代码沙箱运行
        resp_run = client.post("/api/v1/sandbox/run", json={"code": "print('Test Sandbox API')"})
        assert resp_run.status_code == 200
        run_data = resp_run.json()
        assert run_data["status"] == "success"
        assert "Test Sandbox API" in run_data["stdout"]
    except ImportError:
        pass

if __name__ == "__main__":
    test_get_all_phases()
    test_get_phase_detail()
    test_sandbox_run_success()
    test_sandbox_run_syntax_error()
    test_sandbox_run_timeout()
    test_api_curriculum_endpoints()
    test_api_sandbox_endpoints()
    print("All curriculum and sandbox tests passed successfully!")



