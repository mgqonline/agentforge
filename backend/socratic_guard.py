# -*- coding: utf-8 -*-
"""
================================================================================
苏格拉底教学输出护栏 (Socratic Guardrail)
================================================================================

[为什么需要这一层]
AgentForge 是学习系统，导师 Agent 被刻意限定为「苏格拉底式启发」——只引导思考，
不直接给答案。但仅仅在 system prompt 里写「严禁给出完整代码」是**软约束**：
大模型在长对话、强诱导（“我快截止了，直接给我答案”）或多次追问下，很容易
破防，把整份可复制过关的解答贴出来。一旦发生，学员的思考过程就被跳过了，
教学效果归零，而这个失败在日志里完全看不见。

本模块把这条约束变成**硬校验**：导师输出在返回给前端之前，先过一遍护栏，
发现泄题就就地改写为启发式线索，并记录命中原因，供审计与调参。

[拦截的两类泄题]
1. 成块的完整解题代码：```python 代码块里出现了函数/类的完整定义，
   且规模足以直接复制过关（默认阈值：非空行 >= 6，或同时出现 def 与 return）。
2. 散文式答案：没有代码块，但逐条给出「第一步做 X、第二步做 Y」式的
   可照抄实现步骤（命中 >= 2 条强指令式步骤描述）。

[明确不拦截的内容]
- 单个函数名、变量名、库名、报错原文等行内反引号内容；
- 报错根因解读、嫌疑行定位、思考题、知识手册导航（这些是护栏鼓励的输出）；
- 只有一两行的伪代码线索。

[调用方式]
    from socratic_guard import socratic_guard
    safe_text, report = socratic_guard.enforce(text, is_troubleshooting=True)
    if not report["passed"]:
        ...  # report["reasons"] 记录命中原因，report["stripped_code_blocks"] 记录改写块数
"""

import re
from typing import Any, Dict, List, Tuple

try:
    from langsmith import traceable
except ImportError:  # 本地未安装 langsmith 时保持可用
    def traceable(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator


# ---------------------------------------------------------------------------
# 检测规则
# ---------------------------------------------------------------------------

# 围栏代码块：```lang\n ... \n``` （常见于 markdown 输出）
_FENCED_BLOCK_RE = re.compile(r"```([a-zA-Z0-9_+-]*)\n(.*?)(?:```|$)", re.DOTALL)

# 一次「复述答案」的指令式措辞，用于判定散文式泄题
_STEP_HINT_WORDS = (
    "第一步", "第二步", "第三步", "第四步",
    "首先", "然后", "接着", "最后",
    "正确做法是", "正确写法", "应该这样写", "改成这样", "照抄", "直接复制",
    "完整代码", "完整实现", "参考答案", "标准答案", "answer key",
)

# 只在「解题语境」下才视为泄题的措辞（避免把纯讲解误判）
_SOLUTION_WORDS = ("实现", "写法", "代码如下", "应该写", "解决方案", "修复方式", "改法", "正确代码")


class SocraticGuard:
    """导师输出护栏：拦截可复制过关的答案，保留启发式内容。"""

    # 超过这个非空行数，代码块被视为「可复制过关的完整答案」
    MAX_HINT_CODE_LINES = 6
    # 散文式步骤命中达到这个数量，判定为逐条给出解法
    MAX_STEP_HINTS = 2

    def __init__(self, max_hint_code_lines: int = 6, max_step_hints: int = 2):
        self.max_hint_code_lines = max_hint_code_lines
        self.max_step_hints = max_step_hints

    # ---------------- 内部工具 ----------------

    @staticmethod
    def _count_code_lines(code: str) -> int:
        return len([ln for ln in code.splitlines() if ln.strip()])

    @staticmethod
    def _is_full_solution_block(code: str) -> bool:
        """判断代码块是否构成「完整解题答案」而非伪代码线索。"""
        stripped = code.strip()
        if not stripped:
            return False

        lines = [ln for ln in stripped.splitlines() if ln.strip()]
        has_def = any(re.match(r"\s*(async\s+)?def\s+\w+", ln) for ln in lines)
        has_class = any(re.match(r"\s*class\s+\w+", ln) for ln in lines)
        has_return = any(re.match(r"\s*return\b", ln) for ln in lines)
        # 中文注释掉的行不算实现体
        code_only = [ln for ln in lines if not ln.strip().startswith("#")]

        # 出现了函数/类定义，且规模足以直接提交，即视为完整答案
        if has_def or has_class:
            if len(code_only) >= SocraticGuard.MAX_HINT_CODE_LINES:
                return True
            # 短函数也一样危险：有 def 又有 return 基本等于现成答案
            if has_def and has_return:
                return True
        return False

    @classmethod
    def _extract_solution_blocks(cls, text: str) -> List[str]:
        """取出所有被判定为完整答案的代码块原文，便于日志与审计。"""
        found = []
        for match in _FENCED_BLOCK_RE.finditer(text or ""):
            code = match.group(2)
            if cls._is_full_solution_block(code):
                found.append(code.strip())
        return found

    @classmethod
    def _count_step_hints(cls, text: str) -> int:
        """统计散落在正文里的「照抄式步骤」措辞命中数。"""
        if not text:
            return 0
        # 只在提到「解法/实现」时才算，避免把正常的教学点拨算成泄题
        if not any(w in text for w in _SOLUTION_WORDS):
            return 0
        return sum(1 for w in _STEP_HINT_WORDS if w in text)

    # 占位块的起始标记。前端据此识别「这段不是代码」，从而隐藏回填按钮，
    # 因此该标记属于前后端契约，不要随意改动文案（有测试锁定）。
    PLACEHOLDER_MARK = "[教学护栏]"

    @staticmethod
    def _redact_block(code: str) -> str:
        """把完整答案块替换为启发式占位，而不是整段删掉（保留输出结构）。"""
        return (
            "```text\n"
            f"{SocraticGuard.PLACEHOLDER_MARK} 这里原本是可复制的完整实现，已被苏格拉底教学策略拦截。\n"
            "请先按上面的思考支架自行写出第一版，遇到具体报错再回来提问。\n"
            "```"
        )

    # ---------------- 对外接口 ----------------

    @traceable(name="socratic_guard_enforce", tags=["teaching_guardrail", "socratic"])
    def enforce(self, text: str, is_troubleshooting: bool = True) -> Tuple[str, Dict[str, Any]]:
        """
        对导师输出执行护栏校验。

        参数:
            text: 导师生成的 Markdown 文本。
            is_troubleshooting: 是否处于排障场景。排障场景下护栏最严格（默认 True）；
                通关后的架构评审场景允许给出对比性代码示例，因此宽一些。

        返回:
            (改写后的文本, 报告字典)
            报告字段: passed / reasons / stripped_code_blocks / step_hints
        """
        report: Dict[str, Any] = {
            "passed": True,
            "reasons": [],
            "stripped_code_blocks": 0,
            "step_hints": 0,
        }
        if not text or not isinstance(text, str):
            return text, report

        # 1) 拦截成块的完整代码
        stripped_count = 0

        def _replace(match: re.Match) -> str:
            nonlocal stripped_count
            code = match.group(2)
            if self._is_full_solution_block(code):
                stripped_count += 1
                return self._redact_block(code)
            return match.group(0)

        guarded_text = _FENCED_BLOCK_RE.sub(_replace, text)

        if stripped_count:
            report["passed"] = False
            report["stripped_code_blocks"] = stripped_count
            report["reasons"].append(
                f"检测到 {stripped_count} 处可直接复制过关的完整解题代码块，已替换为启发式占位"
            )

        # 2) 拦截散文式解法（仅排障场景；评审场景允许给出方案描述）
        if is_troubleshooting:
            step_hints = self._count_step_hints(guarded_text)
            report["step_hints"] = step_hints
            if step_hints >= self.max_step_hints:
                report["passed"] = False
                report["reasons"].append(
                    f"正文出现 {step_hints} 处逐条照抄式解法措辞，已触发苏格拉底教学告警"
                )

        if not report["passed"]:
            print(f"[🛡️ Socratic Guard] 拦截导师泄题输出: {'; '.join(report['reasons'])}")

        return guarded_text, report

    def inspect(self, text: str, is_troubleshooting: bool = True) -> Dict[str, Any]:
        """只体检不修改，便于测试与离线调参。"""
        _, report = self.enforce(text, is_troubleshooting=is_troubleshooting)
        report["solution_blocks"] = self._extract_solution_blocks(text)
        return report


# 全局单例
socratic_guard = SocraticGuard()