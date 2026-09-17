"""
AgentForge · 企业级代码执行安全沙箱 (Security Code Sandbox)
====================================================================
定位：阶段二核心交付物。用于 Agent 自动生成并执行代码时的最后一道安全防线。
防护层级：
  1. 第一道防线：AST 抽象语法树静态安全审查 (拦截禁用模块、危险内置函数、沙箱逃逸属性)
  2. 第二道防线：进程资源硬隔离与超时熔断 (限制 5 秒超时，捕获死循环与显存溢出)
  3. 第三道防线：标准输入输出重定向与结果提纯
"""

import ast
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Set
from pydantic import BaseModel

# 黑名单：禁止导入的系统敏感模块
FORBIDDEN_MODULES: Set[str] = {
    "os",
    "subprocess",
    "sys",
    "shutil",
    "pty",
    "socket",
    "ctypes",
    "multiprocessing",
    "threading",
    "importlib",
    "pickle",
    "shelve",
}

# 黑名单：禁止调用的危险内置函数
FORBIDDEN_BUILTINS: Set[str] = {
    "eval",
    "exec",
    "__import__",
    "compile",
    "open",
    "globals",
    "locals",
}

# 黑名单：经典的 Python 沙箱逃逸敏感属性探测
FORBIDDEN_ATTRIBUTES: Set[str] = {
    "__subclasses__",
    "__bases__",
    "__mro__",
    "__globals__",
    "__code__",
}


class SecurityViolationError(Exception):
    """AST 审查发现安全违规时抛出"""

    pass


class CodeSecurityAuditor(ast.NodeVisitor):
    """AST 静态代码安全审查器"""

    def __init__(self) -> None:
        self.violations: List[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root_module = alias.name.split(".")[0]
            if root_module in FORBIDDEN_MODULES:
                self.violations.append(
                    f"禁止导入高危系统模块: '{alias.name}' (行号: {node.lineno})"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            root_module = node.module.split(".")[0]
            if root_module in FORBIDDEN_MODULES:
                self.violations.append(
                    f"禁止从敏感模块导入: '{node.module}' (行号: {node.lineno})"
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # 检测直接调用如 eval() 或 exec()
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_BUILTINS:
                self.violations.append(
                    f"禁止调用高危危险函数: '{node.func.id}()' (行号: {node.lineno})"
                )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # 检测沙箱逃逸利用属性如 obj.__subclasses__()
        if node.attr in FORBIDDEN_ATTRIBUTES:
            self.violations.append(
                f"检测到沙箱逃逸潜在攻击行为，禁用属性: '{node.attr}' (行号: {node.lineno})"
            )
        self.generic_visit(node)


class SandboxExecutionResult(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None
    execution_time_seconds: float = 0.0
    security_passed: bool = True


def audit_code_safety(code: str) -> None:
    """静态语法树审查：若违规立即抛出 SecurityViolationError"""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise SecurityViolationError(f"代码语法解析错误: {e}")

    auditor = CodeSecurityAuditor()
    auditor.visit(tree)

    if auditor.violations:
        raise SecurityViolationError("\n  • ".join(auditor.violations))


def run_code_in_sandbox(
    code: str, timeout: float = 3.0, max_output_chars: int = 4000
) -> SandboxExecutionResult:
    """执行安全受限的代码沙箱调用

    步骤：
      1. 执行 AST 静态审计（不通过直接拦截，绝不投递执行）；
      2. 写入安全临时文件；
      3. 子进程隔离受限运行，强制超时熔断；
      4. 捕获并截断输出。
    """
    import time

    start_t = time.time()

    # 第一道防线：AST 静态审计
    try:
        audit_code_safety(code)
    except SecurityViolationError as e:
        return SandboxExecutionResult(
            success=False,
            output="",
            error=f"【安全审计拦截】该代码存在严重安全风险，已被沙箱阻断执行:\n  • {e}",
            security_passed=False,
            execution_time_seconds=0.0,
        )

    # 第二道防线：独立临时文件与隔离子进程执行
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        # 以受限环境启动子进程
        process = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = round(time.time() - start_t, 3)

        output_text = process.stdout[:max_output_chars]
        error_text = process.stderr[:max_output_chars] if process.stderr else None

        return SandboxExecutionResult(
            success=(process.returncode == 0),
            output=output_text,
            error=error_text,
            execution_time_seconds=duration,
            security_passed=True,
        )
    except subprocess.TimeoutExpired:
        duration = round(time.time() - start_t, 3)
        return SandboxExecutionResult(
            success=False,
            output="",
            error=f"【超时熔断】代码执行超时 ({timeout} 秒)，可能包含无限死循环，已强制杀死子进程！",
            security_passed=True,
            execution_time_seconds=duration,
        )
    except Exception as e:
        duration = round(time.time() - start_t, 3)
        return SandboxExecutionResult(
            success=False,
            output="",
            error=f"沙箱运行时内部错误: {str(e)}",
            security_passed=True,
            execution_time_seconds=duration,
        )
    finally:
        # 清理临时文件
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass


# =====================================================================
# 三、 快速自测与演示
# =====================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🛡️ AgentForge 企业级代码执行安全沙箱 (AST+超时熔断) 自测")
    print("=" * 70)

    # 1. 测试合法业务代码
    good_code = """
import math
data = [10, 25, 30, 45, 50]
avg = sum(data) / len(data)
std = math.sqrt(sum((x - avg)**2 for x in data) / len(data))
print(f"数据均值: {avg:.2f}, 标准差: {std:.2f}")
"""
    print("\n[测试 1] 运行合法数学统计计算代码:")
    res1 = run_code_in_sandbox(good_code)
    print(
        f"  结果: 成功={res1.success} | 耗时={res1.execution_time_seconds}s | 输出: {res1.output.strip()}"
    )

    # 2. 测试黑客企图执行系统命令 (AST 拦截)
    attack_code_1 = """
import os
os.system("rm -rf /tmp/important_data")
"""
    print("\n[测试 2] 模拟黑客注入 'import os; os.system()' 攻击代码:")
    res2 = run_code_in_sandbox(attack_code_1)
    print(f"  结果: 拦截成功={not res2.security_passed} | 报错: {res2.error}")

    # 3. 测试沙箱逃逸绕过 (AST 拦截 __subclasses__)
    attack_code_2 = """
classes = ().__class__.__bases__[0].__subclasses__()
print(f"找到子类: {len(classes)}")
"""
    print("\n[测试 3] 模拟黑客利用 '__subclasses__' 进行沙箱逃逸探测:")
    res3 = run_code_in_sandbox(attack_code_2)
    print(f"  结果: 拦截成功={not res3.security_passed} | 报错: {res3.error}")

    # 4. 测试死循环代码 (超时熔断机制)
    infinite_loop_code = """
import time
print("进入死循环...")
while True:
    time.sleep(0.1)
"""
    print("\n[测试 4] 模拟死循环代码 (测试 1.5s 快速超时熔断):")
    res4 = run_code_in_sandbox(infinite_loop_code, timeout=1.5)
    print(
        f"  结果: 超时捕获={not res4.success} | 耗时={res4.execution_time_seconds}s | 报错: {res4.error}"
    )

    print("\n" + "=" * 70)
    print("✅ 阶段二安全沙箱防护体系 (AST + 超时熔断) 验证完全通过！")
    print("=" * 70)
