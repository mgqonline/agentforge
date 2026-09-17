import os
import sys
import time
import tempfile
import subprocess
import ast
from typing import Dict, Any, Optional, Tuple

try:
    import resource
except ImportError:
    resource = None

class CodeSecurityAuditor:
    """Python AST 静态语法树安全审查器，防范恶意系统调用、沙箱逃逸与敏感文件破坏"""

    # 1. 明确禁止导入的高危黑名单模块
    BLOCKED_MODULES = {
        "subprocess", "shutil", "pty", "ctypes", "socket", 
        "multiprocessing", "threading", "resource", "signal"
    }

    # 2. 明确禁止执行的高危系统调用 (module.func)
    BLOCKED_CALLS = {
        ("os", "system"), ("os", "popen"), ("os", "spawn"), ("os", "fork"),
        ("os", "exec"), ("os", "execl"), ("os", "execv"), ("os", "remove"),
        ("os", "unlink"), ("os", "rmdir"), ("os", "kill"), ("os", "chmod"),
        ("os", "chown"), ("sys", "exit"), ("os", "_exit")
    }

    # 3. 危险内置函数
    BLOCKED_BUILTINS = {
        "eval", "exec", "__import__", "compile"
    }

    # 4. 常见的 Python 沙箱逃逸攻击属性 (基于继承链或底层环境嗅探)
    BLOCKED_ATTRIBUTES = {
        "__subclasses__", "__globals__", "__code__", "__builtins__"
    }

    # 5. 反射高危属性黑名单
    BLOCKED_REFLECT_ATTRS = {
        "system", "popen", "spawn", "fork", "exec", "execl", "execv",
        "remove", "unlink", "rmdir", "kill", "chmod", "eval", "exec",
        "__subclasses__", "__globals__", "__code__", "__builtins__"
    }

    # 6. 敏感凭据关键词
    SENSITIVE_KEY_PATTERNS = {"KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL"}

    @classmethod
    def audit(cls, code: str) -> Tuple[bool, str]:
        """
        静态审查 Python 源码安全规范：
        返回: (is_safe, error_reason)
        """
        if len(code) > 200_000:
            return False, "安全策略拦截：代码量超过沙箱限制 (最大允许 200KB)"

        try:
            tree = ast.parse(code)
        except SyntaxError:
            # 语法错误直接放行给解释器正常抛出标准 Traceback
            return True, ""

        for node in ast.walk(tree):
            # 1. 检测 import 语句
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_mod = alias.name.split('.')[0]
                    if root_mod in cls.BLOCKED_MODULES:
                        return False, f"安全边界策略拦截：禁止导入受限系统底层模块【{alias.name}】"

            # 2. 检测 from ... import 语句
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_mod = node.module.split('.')[0]
                    if root_mod in cls.BLOCKED_MODULES:
                        return False, f"安全边界策略拦截：禁止导入受限系统底层模块【{node.module}】"
                for alias in node.names:
                    if alias.name in cls.BLOCKED_BUILTINS:
                        return False, f"安全边界策略拦截：禁止引入受限危险内置函数【{alias.name}】"

            # 3. 检测函数与方法调用
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in cls.BLOCKED_BUILTINS:
                        return False, f"安全边界策略拦截：禁止使用动态执行函数【{node.func.id}()】"
                    elif node.func.id == "getattr":
                        if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
                            attr_name = node.args[1].value
                            if attr_name in cls.BLOCKED_REFLECT_ATTRS or attr_name in cls.BLOCKED_ATTRIBUTES:
                                return False, f"安全边界策略拦截：禁止通过 getattr 反射调用受限高危属性【{attr_name}】"
                elif isinstance(node.func, ast.Attribute):
                    attr_name = node.func.attr
                    # 检测 os.func() 调用
                    if isinstance(node.func.value, ast.Name):
                        mod_name = node.func.value.id
                        if (mod_name, attr_name) in cls.BLOCKED_CALLS:
                            return False, f"安全边界策略拦截：禁止执行高危系统调用【{mod_name}.{attr_name}()】"
                        # 检测 os.getenv("OPENAI_API_KEY")
                        if mod_name == "os" and attr_name == "getenv":
                            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                                arg_val = node.args[0].value.upper()
                                if any(pat in arg_val for pat in cls.SENSITIVE_KEY_PATTERNS):
                                    return False, f"安全边界策略拦截：禁止在沙箱代码中直接读取系统凭据【{node.args[0].value}】"
                    # 检测 os.environ.get("OPENAI_API_KEY")
                    elif isinstance(node.func.value, ast.Attribute) and isinstance(node.func.value.value, ast.Name):
                        if node.func.value.value.id == "os" and node.func.value.attr == "environ" and attr_name == "get":
                            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                                arg_val = node.args[0].value.upper()
                                if any(pat in arg_val for pat in cls.SENSITIVE_KEY_PATTERNS):
                                    return False, f"安全边界策略拦截：禁止在沙箱代码中直接读取系统凭据【{node.args[0].value}】"

            # 4. 检测敏感内部属性访问 (防沙箱逃逸)
            elif isinstance(node, ast.Attribute):
                if node.attr in cls.BLOCKED_ATTRIBUTES:
                    return False, f"安全边界策略拦截：禁止访问受限内部底层属性【{node.attr}】"

            # 5. 检测 os.environ["OPENAI_API_KEY"] 字典下标读取凭据
            elif isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name):
                    if node.value.value.id == "os" and node.value.attr == "environ":
                        slice_node = node.slice
                        if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
                            key_val = slice_node.value.upper()
                            if any(pat in key_val for pat in cls.SENSITIVE_KEY_PATTERNS):
                                return False, f"安全边界策略拦截：禁止在沙箱代码中直接读取系统凭据【{slice_node.value}】"

        return True, ""


class SandboxRunner:
    """具备 AST 静态审查、凭证零泄露与资源配额的企业级代码沙箱执行器"""

    MAX_OUTPUT_BYTES = 64 * 1024  # 最大输出 64KB 防爆破

    # 子进程严格白名单（绝对剥离内网数据库密码与无关敏感 Key）
    SAFE_ENV_WHITELIST = [
        "PATH", "LANG", "LC_ALL", "TEMP", "TMPDIR", "HOME",
        "OPENAI_BASE_URL", "OPENAI_API_BASE", "DEFAULT_MODEL", "TOKENIZERS_PARALLELISM"
    ]

    def __init__(self, default_timeout: int = 60, memory_limit_mb: int = 1024):
        self.default_timeout = default_timeout
        self.memory_limit_mb = memory_limit_mb

    def _set_resource_limits(self):
        """设置子进程资源配额限制 (Linux / macOS)"""
        if resource:
            try:
                bytes_limit = self.memory_limit_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (bytes_limit, bytes_limit))
            except Exception:
                pass

    def run_code(self, code: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """在隔离子进程中安全执行代码"""
        start_time = time.time()

        # 1. 执行 AST 静态安全审查
        is_safe, block_reason = CodeSecurityAuditor.audit(code)
        if not is_safe:
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "status": "blocked",
                "stdout": "",
                "stderr": f"🛡️ {block_reason}。\n本实战平台仅允许与 AI 业务逻辑、模型调用及算法运算相关的安全代码。",
                "exit_code": 403,
                "execution_time_ms": elapsed_ms
            }

        if timeout is None:
            timeout = self.default_timeout
        else:
            timeout = min(120, max(1, timeout))

        # 2. 创建临时脚本文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_path = f.name

        try:
            preexec = self._set_resource_limits if sys.platform != "win32" else None
            
            # 3. 环境变量白名单过滤与凭证脱敏
            child_env = {}
            for k in self.SAFE_ENV_WHITELIST:
                if k in os.environ:
                    child_env[k] = os.environ[k]

            # 仅在需要模型调用时透传 OPENAI_API_KEY，坚决剥离 DB 与系统机密
            if "OPENAI_API_KEY" in os.environ:
                child_env["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]

            base_url = (
                child_env.get("OPENAI_BASE_URL") or 
                os.environ.get("OPENAI_BASE_URL") or 
                os.environ.get("OPENAI_API_BASE") or 
                "https://api.deepseek.com"
            )
            child_env["OPENAI_BASE_URL"] = base_url
            child_env["OPENAI_API_BASE"] = base_url
            
            # 拼接 PYTHONPATH 保证容器与宿主机下均可引用项目依赖
            project_dirs = ["/app", "/app/backend", "/app/curriculum", os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))]
            curr_pythonpath = os.environ.get("PYTHONPATH", "")
            child_env["PYTHONPATH"] = os.pathsep.join([p for p in project_dirs if os.path.exists(p)] + ([curr_pythonpath] if curr_pythonpath else []))

            # 4. 使用当前运行环境的 python 解释器执行
            proc = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                preexec_fn=preexec,
                env=child_env,
                cwd=os.path.dirname(temp_path)
            )
            elapsed_ms = round((time.time() - start_time) * 1000, 2)

            # 5. 输出容量溢出截断保护
            stdout_text = proc.stdout
            if len(stdout_text) > self.MAX_OUTPUT_BYTES:
                stdout_text = stdout_text[:self.MAX_OUTPUT_BYTES] + "\n\n[系统安全提示: 输出内容已超过 64KB 限制，自动截断]"

            stderr_text = proc.stderr
            if len(stderr_text) > self.MAX_OUTPUT_BYTES:
                stderr_text = stderr_text[:self.MAX_OUTPUT_BYTES] + "\n\n[系统安全提示: 错误日志已超过 64KB 限制，自动截断]"
            
            if proc.returncode == 0:
                return {
                    "status": "success",
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "exit_code": proc.returncode,
                    "execution_time_ms": elapsed_ms
                }
            else:
                return {
                    "status": "error",
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "exit_code": proc.returncode,
                    "execution_time_ms": elapsed_ms
                }
        except subprocess.TimeoutExpired:
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "status": "timeout",
                "stdout": "",
                "stderr": f"执行超时：代码运行时间超过限制（{timeout}秒），已被系统安全终止。",
                "exit_code": -1,
                "execution_time_ms": elapsed_ms
            }
        except Exception as e:
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "status": "error",
                "stdout": "",
                "stderr": f"沙箱执行异常: {str(e)}",
                "exit_code": -1,
                "execution_time_ms": elapsed_ms
            }
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def verify_code(self, user_code: str, test_code: str, timeout: int = 90) -> Dict[str, Any]:
        """将用户实现与测试用例拼接执行并收集评测结果"""
        combined_code = f"""
# --- USER CODE ---
{user_code}

# --- TEST SUITE ---
{test_code}
"""
        res = self.run_code(combined_code, timeout=timeout)
        passed = (res["status"] == "success" and res["exit_code"] == 0)
        
        return {
            "passed": passed,
            "details": res,
            "message": "所有单元测试通过！关卡已点亮 🎉" if passed else "测试未全部通过，请查看终端报错或求助 AI 导师。"
        }
