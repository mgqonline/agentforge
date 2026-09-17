"""
Agent 隔离沙箱与高可用执行器 (Docker / Subprocess Isolation)
============================================================
功能特性：
  1. 支持将 Agent 生成的代码隔离运行在微型容器环境或进程级限制沙箱中
  2. 超时截断、内存资源限制与文件防护策略
"""

import subprocess
import tempfile
import os
import sys
from typing import Dict, Any

class SecureSandboxRunner:
    def __init__(self, timeout_seconds: int = 10):
        self.timeout_seconds = timeout_seconds

    def execute_python_code(self, code: str) -> Dict[str, Any]:
        """
        在临时隔离目录中安全运行 Python 代码。
        若系统已开启 Docker 且支持隔离镜像，自动切换为 Docker 沙箱；
        否则自动降级为受限子进程沙箱。
        """
        # 1. 尝试 Docker 沙箱隔离
        docker_result = self._try_execute_docker(code)
        if docker_result is not None:
            return docker_result

        # 2. 降级为受限子进程隔离环境
        return self._execute_subprocess_isolated(code)

    def _try_execute_docker(self, code: str) -> Any:
        """检查并尝试在 Docker 实例中无痕执行"""
        try:
            # 检查 docker 命令可用性
            chk = subprocess.run(["docker", "info"], capture_output=True, timeout=2)
            if chk.returncode != 0:
                return None
            
            with tempfile.TemporaryDirectory() as tmpdir:
                script_path = os.path.join(tmpdir, "script.py")
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(code)
                
                cmd = [
                    "docker", "run", "--rm",
                    "--network", "none",            # 禁用容器网络访问连接
                    "--memory", "128m",             # 限制内存 128MB
                    "-v", f"{script_path}:/app/script.py:ro",
                    "python:3.10-slim",
                    "python", "/app/script.py"
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout_seconds)
                return {
                    "sandbox_type": "docker",
                    "stdout": res.stdout,
                    "stderr": res.stderr,
                    "exit_code": res.returncode
                }
        except Exception:
            return None

    def _execute_subprocess_isolated(self, code: str) -> Dict[str, Any]:
        """子进程沙箱（超时与环境变量限制）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = os.path.join(tmpdir, "isolated_script.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)
            
            # 清理敏感环境变量传递
            restricted_env = {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONPATH": tmpdir
            }
            
            try:
                res = subprocess.run(
                    [sys.executable, script_path],
                    cwd=tmpdir,
                    env=restricted_env,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds
                )
                return {
                    "sandbox_type": "subprocess_isolated",
                    "stdout": res.stdout,
                    "stderr": res.stderr,
                    "exit_code": res.returncode
                }
            except subprocess.TimeoutExpired:
                return {
                    "sandbox_type": "subprocess_isolated",
                    "stdout": "",
                    "stderr": f"❌ 运行超时！已在 {self.timeout_seconds}s 后强行终止。",
                    "exit_code": -1
                }


if __name__ == "__main__":
    runner = SecureSandboxRunner(timeout_seconds=5)
    test_code = """
import sys
print('Hello from Agent Sandbox!')
print('Python version:', sys.version.split()[0])
"""
    result = runner.execute_python_code(test_code)
    print("📦 沙箱隔离测试结果:")
    print(f"  - 隔离模式: {result['sandbox_type']}")
    print(f"  - 输出: {result['stdout'].strip()}")
    print(f"  - 退出码: {result['exit_code']}")
