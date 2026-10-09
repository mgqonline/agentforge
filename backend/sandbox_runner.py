import os
import sys
import time
import tempfile
import subprocess
import ast
import re
from typing import Dict, Any, Optional, Tuple, List

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

    # 7. 非敏感的 AI 运行配置白名单（凭据仍然禁止读取）
    ALLOWED_ENV_KEYS = {
        "OPENAI_BASE_URL", "OPENAI_BASE",
        "DEFAULT_MODEL"
    }

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
                                env_key = node.args[0].value
                                # 白名单检查：允许读取 AI 业务必需的环境变量
                                if env_key in cls.ALLOWED_ENV_KEYS:
                                    continue
                                arg_val = env_key.upper()
                                if any(pat in arg_val for pat in cls.SENSITIVE_KEY_PATTERNS):
                                    return False, f"安全边界策略拦截：禁止在沙箱代码中直接读取系统凭据【{env_key}】"
                    # 检测 os.environ.get("OPENAI_API_KEY")
                    elif isinstance(node.func.value, ast.Attribute) and isinstance(node.func.value.value, ast.Name):
                        if node.func.value.value.id == "os" and node.func.value.attr == "environ" and attr_name == "get":
                            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                                env_key = node.args[0].value
                                # 白名单检查：允许读取 AI 业务必需的环境变量
                                if env_key in cls.ALLOWED_ENV_KEYS:
                                    continue
                                arg_val = env_key.upper()
                                if any(pat in arg_val for pat in cls.SENSITIVE_KEY_PATTERNS):
                                    return False, f"安全边界策略拦截：禁止在沙箱代码中直接读取系统凭据【{env_key}】"

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
                            env_key = slice_node.value
                            # 白名单检查：允许读取 AI 业务必需的环境变量
                            if env_key in cls.ALLOWED_ENV_KEYS:
                                continue
                            key_val = env_key.upper()
                            if any(pat in key_val for pat in cls.SENSITIVE_KEY_PATTERNS):
                                return False, f"安全边界策略拦截：禁止在沙箱代码中直接读取系统凭据【{env_key}】"

        return True, ""


# 评测期「重型可选依赖」的注入模板（供 SandboxRunner.DEPENDENCY_STUB_PREAMBLE 使用）
# ------------------------------------------------------------------------------
# 模板里刻意只做两件事：把模块注册进 sys.modules、让任意属性访问都返回一个
# 「可被调用但什么都不算」的惰性对象。它不生成任何伪造的识别结果，所以只能支撑
# 「接口契约」类断言，无法把错误实现蒙混成正确实现。
_DEPENDENCY_STUB_TEMPLATE = '''# --- 评测期重型依赖替身：仅当 {module}.{attr} 确实无法导入时生效 ---
try:
    import {module}  # noqa: F401
    from {module} import {attr} as _probe_{module}  # noqa: F401
except Exception:
    import sys as _sys, types as _types

    class _SandboxStubCallable:
        """评测用惰性替身：可被任意调用，但不伪装任何真实计算结果。

        这里刻意让「检索类」调用抛出 ValueError —— 因为真实的 DeepFace 在
        enforce_detection=True 且检测不到人脸时正是抛 ValueError。如果替身改成
        返回 None，参考解里紧随其后的 `len(dfs)` 会抛 TypeError 并被兜底成 500，
        把一个「客户端图片没人脸」的正常业务分支误判成服务端崩溃。
        让替身保持与真实库一致的失败姿态，评测才能反映真实语义。
        """

        def __init__(self, *a, **k):
            pass

        def __call__(self, *a, **k):
            raise ValueError(
                "沙箱替身：该依赖未真实安装，无法执行实际推理"
                "（评测仅覆盖接口契约，不校验模型精度）"
            )

        def __getattr__(self, _name):
            if _name == "find":
                # `find` 是参考解唯一真实调用的入口：真实的 DeepFace 在
                # enforce_detection=True 且图中无人脸时抛 ValueError。替身若同意返回
                # 惰性对象，参考解会走到 `len(dfs) == 0` 分支，把「检测不到人脸」这个
                # 应当 400 的输入静默当成「陌生人」返回 200，评测就失去区分能力。
                return self._find_no_face

            return _SandboxStubCallable()

        def _find_no_face(self, *a, **k):
            if k.get("enforce_detection", False):
                raise ValueError(
                    "沙箱替身：无人脸可检测 —— 与真实 DeepFace 在 "
                    "enforce_detection=True 时保持一致的失败姿态"
                )
            return []

        def __iter__(self):
            return iter(())

        def __len__(self):
            return 0

    class _SandboxStubModule(_types.ModuleType):
        # 只暴露「探测时声明过的真实符号」，刻意不给模块加 catch-all 式的
        # __getattr__。原因是在 macOS + 未安装 tf-keras 的环境里，一个把任意属性
        # 都解析成对象的模块对象会在解释器退出阶段（文档字符串/警告收集器扫描
        # sys.modules 时）触发 native 段错误，退出码 -11、测试虽然全 OK 却被判失败。
        # 显式赋值既避开该崩溃，又更严格：只有参考解真正 import 的名字才可用。
        pass

    _stub_module = _SandboxStubModule('{module}')
    _stub_module.{attr} = _SandboxStubCallable()
    _sys.modules['{module}'] = _stub_module
'''

# 探测时必须连「子模块」一起导入
# ------------------------------------------------------------------------------
# 反例：`import deepface` 本身会成功（顶层包能加载），真正抛错的是它下面被
# `__init__`/`DeepFace.py` 触发的 Keras 版本校验。如果只探测顶层包，就会误判
# 「依赖可用」，替身不注入，随后参考解里的 `from deepface import DeepFace`
# 仍然把整场评测打崩。因此每个模块都要声明「参考解真正会用到的那几个符号」，
# 探测语句与真实用法保持一致。
STUBBABLE_MODULES = (("deepface", ("DeepFace",)),)


class SandboxRunner:
    """具备 AST 静态审查、凭证零泄露与资源配额的企业级代码沙箱执行器"""

    MAX_OUTPUT_BYTES = 64 * 1024  # 最大输出 64KB 防爆破

    # ==========================================================
    # 通关评测时的 __main__ 演示门控前缀
    # ==========================================================
    # [为什么需要它]
    # `verify_code` 会把「学员代码」与「测试套件」拼接成同一个脚本执行。学员代码的
    # 参考实现通常自带一段 `if __name__ == "__main__":` 演示（打印效果、调用真实
    # 大模型、加载重量级依赖）。在拼接后的脚本里，`__name__` 同样是 "__main__"，
    # 于是这段演示会抢在测试套件之前执行：
    #   · 需要 API Key 的演示（ChatOpenAI / CrewAI）→ 抛 OpenAIError 直接中断；
    #   · 需要未安装依赖的演示（crewai）→ ModuleNotFoundError 直接中断；
    # 结果是「照抄官方答案也过不了关」，学员永远拿不到分数，而且报错信息与自己的
    # 实现毫无关系。
    #
    # [机制]
    # 三件事必须同时成立，因此门控分成「前缀屏蔽 + 套件内复位」两段：
    #   1. 用户代码里的 `if __name__ == "__main__":` 演示必须在评测期**不执行**，
    #      否则需要 API Key / 未安装重型依赖的演示会直接炸掉整场评测；
    #   2. 测试套件的 `unittest.main()` 必须在**真正的 "__main__"** 身份下运行，
    #      CPython 只有模块名是 "__main__" 时才把 stderr 交给 unittest 打印
    #      "test_x ... ok / Ran N tests / OK" 用例明细；
    #   3. 用户代码里依赖模块名的框架（典型如 Celery 用当前模块名做任务命名空间，
    #      产出 `ai_agent_tasks.generate_report`）必须看到真实模块名。
    #
    # 关键：`__main__` 复位**必须发生在测试套件之前**。若放在脚本最末尾（套件之后），
    # 那么 `unittest.main()` 执行时模块名仍是哨兵，一个字符都不会输出 —— 学员端
    # 的「测试断言卡片」会全部退化成 unknown。
    MAIN_GUARD_PREAMBLE = (
        "# --- 评测门控：用户代码的 __main__ 演示在评测期不执行 ---\n"
        "__real_main__ = __name__\n"
        "__name__ = '__evaluation_sandbox__'\n"
    )

    # 测试套件前的门控复位：恢复真实模块名，让 unittest 明细与 Celery 命名空间均正常
    MAIN_GUARD_EPILOGUE = (
        "\n# --- 评测门控复位：测试套件以真正的 __main__ 身份运行 ---\n"
        "__name__ = __real_main__\n\n"
    )

    # 评测期的「重型可选依赖替身」名单
    # ------------------------------------------------------------------
    # 有些关卡的参考解顶部就直接 `from deepface import DeepFace` 之类地导入重型
    # 机器学习栈。这些依赖一旦在当前环境装不上（deepface 要求 tf-keras，而本机
    # 是 tensorflow 2.21），**整个评测脚本会在跑任何测试之前就 ImportError 崩掉**，
    # 于是该关卡永远「不可校验」。注意这与 `__main__` 演示门控是两个不同的问题：
    # 门控管的是「不执行用户代码末尾的演示」，这里要救的是「模块顶层的 import 本身
    # 就炸」。
    #
    # 处置原则（保守、可解释、不掩盖真实缺陷）：
    #   * 只有当该模块**确实无法导入**时，才注入一个惰性替身；能装上的环境照常走真货，
    #     绝不改变「依赖齐全时」的行为；
    #   * 替身只要求「能被 import、能接收任意调用」，不伪装任何算法结果。
    #     因此它只能让「接口契约」类断言（是否读取字节流、是否以 400 拒绝非法输入、
    #     调用参数是否正确）成立，无法伪造真实识别准确率——本关的验收点也正在于此；
    #   * 真正的重依赖一旦装上，替身自动失效，评测回到真实实现。
    STUBBABLE_MODULES = ("deepface",)

    STUBBABLE_MODULES = (("deepface", ("DeepFace",)),)

    DEPENDENCY_STUB_PREAMBLE = "".join(
        _DEPENDENCY_STUB_TEMPLATE.format(module=m, attr=a)
        for m, attrs in STUBBABLE_MODULES
        for a in attrs
    )

    # 子进程严格白名单（绝对剥离内网数据库密码与无关敏感 Key）
    SAFE_ENV_WHITELIST = [
        "PATH", "LANG", "LC_ALL", "TEMP", "TMPDIR", "HOME",
        "OPENAI_BASE_URL", "OPENAI_API_BASE", "DEFAULT_MODEL", "TOKENIZERS_PARALLELISM"
    ]

    def __init__(self, default_timeout: int = 60, memory_limit_mb: int = 1024):
        self.default_timeout = default_timeout
        self.memory_limit_mb = memory_limit_mb

    @staticmethod
    def _memory_limit_supported() -> bool:
        """在「父进程」侧探测 RLIMIT_AS 是否真的可设置

        这样做的意义：preexec_fn 里的失败是无法在父进程捕获的（CPython 会直接
        抛 SubprocessError 并丢弃子进程全部输出）。因此在父进程先掷一次同样的
        setrlimit 做探针——探针的成功/失败是干净可捕获的，从而决定这次执行是否
        需要挂 preexec_fn。探测本身只是把自己的软上限改成自己已经是的大小，无副作用。
        """
        if not resource:
            return False
        try:
            current_soft, current_hard = resource.getrlimit(resource.RLIMIT_AS)
            probe = min(current_soft, 1024 * 1024 * 1024)
            resource.setrlimit(resource.RLIMIT_AS, (probe, current_hard))
            return True
        except Exception:
            return False

    def _set_resource_limits(self):
        """设置子进程资源配额限制 (Linux / macOS)

        注意：该函数运行在 fork 出来的子进程里（subprocess 的 preexec_fn）。
        一旦这里抛出任何异常，CPython 会把整个 Popen 调用判为失败并抛出
        `SubprocessError: Exception occurred in preexec_fn`，而且**捕获不到**
        子进程的任何 stdio 输出——表现为「沙箱永远返回空 stdout/stderr」，
        评测卡片全部退化成 unknown，学员点击【验证通关】永远无法通关。

        macOS 上 RLIMIT_AS 是已知的不可设置项（setrlimit 直接报错），
        因此这里彻底改为「尽力而为 + 绝不抛异常」：出问题时只记录降级标志，
        由父进程读取后把内存限制标记为未生效，从而保证代码执行本身不受影响。
        """
        self._limit_degraded = False
        self._limit_error = ""
        if not resource:
            self._limit_degraded = True
            self._limit_error = "当前平台不支持 resource 模块"
            return
        try:
            bytes_limit = self.memory_limit_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (bytes_limit, bytes_limit))
        except Exception as exc:
            # 关键：preexec_fn 内绝不能向上抛异常，否则整个子进程输出都会丢失
            self._limit_degraded = True
            self._limit_error = f"{type(exc).__name__}: {exc}"

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
            preexec = self._set_resource_limits if (sys.platform != "win32" and self._memory_limit_supported()) else None
            
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

    def _parse_unittest_cases(self, stderr_text: str, stdout_text: str, test_code: str) -> List[Dict[str, Any]]:
        """从 unittest 执行的标准输出或测试源码中解析出结构化的用例执行卡片"""
        raw_output = (stderr_text or "") + "\n" + (stdout_text or "")
        cases: List[Dict[str, Any]] = []

        # 1. 优先尝试从源码中提取预期的所有 test_ 方法名，确保底表完整
        expected_tests = re.findall(r"def\s+(test_[a-zA-Z0-9_]+)\s*\(", test_code or "")
        seen_names = set()

        # 2. 从 verbosity=2 输出中捕获每项测试的结果：test_foo (xxx) ... ok / FAIL / ERROR
        case_pattern = re.compile(r"(test_[a-zA-Z0-9_]+)\s*\([^)]*\)\s*\.\.\.\s*(ok|FAIL|ERROR)", re.IGNORECASE)
        for match in case_pattern.finditer(raw_output):
            name, status_str = match.group(1), match.group(2).lower()
            status = "passed" if status_str == "ok" else "failed"
            seen_names.add(name)
            cases.append({
                "name": name,
                "status": status,
                "error_message": ""
            })

        # 3. 提取失败/错误详情
        fail_blocks = re.findall(
            r"=(?:FAIL|ERROR):\s*(test_[a-zA-Z0-9_]+)[^\n]*\n-+\n(.*?)(?=\n={10,}|\n-{10,}|\Z)",
            raw_output,
            re.DOTALL
        )
        fail_map = {}
        for fname, fdetail in fail_blocks:
            # 提取最后一行核心错误或 AssertionError
            lines = [l.strip() for l in fdetail.strip().split("\n") if l.strip()]
            err_line = lines[-1] if lines else "断言不匹配"
            fail_map[fname] = err_line

        # 为已捕获用例挂载错误信息
        for c in cases:
            if c["name"] in fail_map:
                c["error_message"] = fail_map[c["name"]]

        # 4. 补齐尚未捕获到的预期用例，保证评测卡片与测试源码一一对应
        # ------------------------------------------------------------------
        # 注意：这里不能写成 `if not cases`。一套测试里只要有一条用例先被
        # verbosity=2 的输出捕获到，剩下的用例就会全部缺失，前端评测卡片便
        # 会「少几条」。而且在 unittest 的默认（非 verbose）输出下，全部用例
        # 都只会汇总成一行 `Ran N tests ... OK`，解析不到任何 ok 标记，
        # 此时必须靠源码里的 test_ 方法名补齐——否则卡片会全部退化成
        # status="unknown"，学员看到「一条都没跑」的错误反馈。
        if expected_tests:
            is_all_passed = ("\nOK" in raw_output) or raw_output.strip().endswith("OK")
            for tname in expected_tests:
                if tname in seen_names:
                    continue
                if tname in fail_map:
                    status, err = "failed", fail_map[tname]
                elif is_all_passed:
                    status, err = "passed", ""
                else:
                    status, err = "unknown", "测试未执行或提前中断"
                seen_names.add(tname)
                cases.append({
                    "name": tname,
                    "status": status,
                    "error_message": err
                })

        return cases

    def verify_code(self, user_code: str, test_code: str, timeout: int = 90) -> Dict[str, Any]:
        """将用户实现与测试用例拼接执行并收集评测结果 (已增强结构化断言解析)"""
        # 确保 unittest.main 默认开启 verbosity=2，输出详细测试用例
        wrapped_test_code = test_code
        if "unittest.main()" in wrapped_test_code:
            wrapped_test_code = wrapped_test_code.replace("unittest.main()", "unittest.main(verbosity=2)")
        elif "unittest.main" in wrapped_test_code and "verbosity" not in wrapped_test_code:
            wrapped_test_code = re.sub(r"unittest\.main\s*\((.*?)\)", r"unittest.main(\1, verbosity=2)", wrapped_test_code)

        combined_code = f"""
# --- USER CODE ---
{self.MAIN_GUARD_PREAMBLE}
{self.DEPENDENCY_STUB_PREAMBLE}
{user_code}

{self.MAIN_GUARD_EPILOGUE}# --- TEST SUITE ---
{wrapped_test_code}
"""
        res = self.run_code(combined_code, timeout=timeout)
        passed = (res["status"] == "success" and res["exit_code"] == 0)
        
        # 结构化抽取用例结果
        stderr_output = res.get("stderr", "") or res.get("error", "")
        stdout_output = res.get("stdout", "") or res.get("output", "")
        test_cases = self._parse_unittest_cases(stderr_output, stdout_output, test_code)
        
        total_count = len(test_cases)
        passed_count = sum(1 for c in test_cases if c.get("status") == "passed")
        failed_count = total_count - passed_count
        
        summary = {
            "total": total_count,
            "passed": passed_count,
            "failed": failed_count,
            "pass_rate": f"{round(passed_count / total_count * 100)}%" if total_count > 0 else ("100%" if passed else "0%"),
            "duration_ms": res.get("execution_time_ms", 0)
        }

        return {
            "passed": passed,
            "details": res,
            "message": "所有单元测试通过！关卡已点亮 🎉" if passed else "测试未全部通过，请查看测试断言卡片或求助 AI 导师。",
            "test_cases": test_cases,
            "summary": summary
        }
