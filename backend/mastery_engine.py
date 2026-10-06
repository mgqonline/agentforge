"""掌握度评估模块 (Mastery Evaluation)

背景
----
本项目是 AI 技术类学习型系统。改造前，学习评分是写死的布尔分支：

    score = 68 if is_error_diagnostic else 88
    level = "B" if is_error_diagnostic else "A"

这导致「一次做对」与「看了答案后试错 20 次才过」得到完全相同的评价，教师也无法
识别真正需要帮助的学员。本模块把评分改为**由可观测证据推导**，并沉淀跨会话的
概念级掌握度画像。

设计原则
--------
1. 证据优先：只使用可客观记录的数据（尝试次数、是否首试通过、耗时、求助次数）。
2. 过程重于结果：通过得慢、反复失败会拉低分数，而不是只看最终 passed。
3. 不惩罚求助：求助只轻微影响分数（鼓励提问，但避免把求助当通关捷径）。
4. 纯函数优先：核心计算是无副作用的纯函数，便于单测与复用。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 一、失败类型识别：把报错归类为可跟踪的「知识薄弱点」
# ---------------------------------------------------------------------------

# 顺序敏感：先匹配具体异常，再匹配宽泛关键词
_FAILURE_KIND_PATTERNS: List[tuple[str, re.Pattern[str]]] = [
    ("assertion", re.compile(r"AssertionError|断言失败|未全部通过", re.IGNORECASE)),
    ("syntax", re.compile(r"SyntaxError|IndentationError|语法", re.IGNORECASE)),
    ("type", re.compile(r"TypeError|类型不匹配", re.IGNORECASE)),
    ("index", re.compile(r"IndexError|KeyError|越界|不存在", re.IGNORECASE)),
    ("name", re.compile(r"NameError|UnboundLocalError", re.IGNORECASE)),
    ("import", re.compile(r"ModuleNotFoundError|ImportError|无法导入", re.IGNORECASE)),
    ("attribute", re.compile(r"AttributeError", re.IGNORECASE)),
    ("value", re.compile(r"ValueError", re.IGNORECASE)),
    ("timeout", re.compile(r"超时|TimeoutError|timed out", re.IGNORECASE)),
    ("security", re.compile(r"安全边界策略拦截|安全策略|沙箱逃逸", re.IGNORECASE)),
    ("runtime", re.compile(r"RuntimeError|Exception|Error", re.IGNORECASE)),
]

# 失败类型 -> 人类可读的薄弱点名称（用于学员画像与导师提示）
FAILURE_KIND_LABELS: Dict[str, str] = {
    "assertion": "结果与预期契约不一致",
    "syntax": "语法与缩进规范",
    "type": "类型与数据结构匹配",
    "index": "索引与键边界处理",
    "name": "变量作用域与命名",
    "import": "依赖与模块导入",
    "attribute": "对象属性与接口调用",
    "value": "取值合法性与边界校验",
    "timeout": "算法效率与死循环排查",
    "security": "沙箱安全边界（受限模块/动态执行）",
    "runtime": "运行时异常排查",
    "unknown": "未归类的执行错误",
}


def classify_failure(error_text: str) -> str:
    """把报错文本归类为稳定的失败类型标识。

    返回 FAILURE_KIND_LABELS 中的键；无法识别时返回 "unknown"。
    """
    text = error_text or ""
    if not text.strip():
        return "unknown"
    for kind, pattern in _FAILURE_KIND_PATTERNS:
        if pattern.search(text):
            return kind
    return "unknown"


def failure_kind_label(kind: str) -> str:
    """返回失败类型的中文可读名称。"""
    return FAILURE_KIND_LABELS.get(kind or "unknown", FAILURE_KIND_LABELS["unknown"])


# ---------------------------------------------------------------------------
# 二、评分模型：由证据推导掌握度
# ---------------------------------------------------------------------------

# 各维度权重，合计 1.0
_WEIGHT_INDEPENDENCE = 0.40   # 独立性：是否首试通过、失败了几次
_WEIGHT_EFFICIENCY = 0.25     # 效率：耗时
_WEIGHT_SELF_RELIANCE = 0.20  # 自主性：求助次数
_WEIGHT_COMPLETION = 0.15     # 完成度：是否最终通过

# 关卡难度基准耗时（毫秒），用于效率归一化
_DEFAULT_BASELINE_MS = 10 * 60 * 1000      # 默认 10 分钟
_DIFFICULTY_BASELINE_MS: Dict[str, int] = {
    "Beginner": 5 * 60 * 1000,
    "Intermediate": 10 * 60 * 1000,
    "Advanced": 20 * 60 * 1000,
}


@dataclass
class MasteryEvidence:
    """一次关卡尝试的可观测证据集合。"""

    attempts_total: int = 0
    attempts_failed: int = 0
    first_attempt_passed: bool = False
    time_spent_ms: int = 0
    hints_used: int = 0
    passed: bool = False
    difficulty: str = ""
    failure_kinds: List[str] = field(default_factory=list)


@dataclass
class MasteryResult:
    """掌握度评估结果。"""

    score: float
    level: str
    dimensions: Dict[str, float]
    rationale: List[str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 1),
            "level": self.level,
            "dimensions": {k: round(v, 1) for k, v in self.dimensions.items()},
            "rationale": self.rationale,
        }


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _baseline_ms(difficulty: str) -> int:
    return _DIFFICULTY_BASELINE_MS.get(difficulty or "", _DEFAULT_BASELINE_MS)


def evaluate_mastery(evidence: MasteryEvidence) -> MasteryResult:
    """由证据推导掌握度评分（纯函数，无副作用）。

    与旧实现的关键差异：分数不再是「有没有提问」的二值分支，而是随
    尝试次数、首试表现、耗时与求助量连续变化。
    """
    attempts_total = max(0, evidence.attempts_total)
    attempts_failed = max(0, min(evidence.attempts_failed, attempts_total))
    rationale: List[str] = []

    # ---- 维度 1：独立性（权重最高）----
    # 首试通过得满分；每失败一次扣 15 分，最低 20 分（体现"最终做出来了"的保底）
    if not evidence.passed:
        independence = 0.0
        rationale.append("尚未通过该关卡，独立性暂不计分。")
    elif evidence.first_attempt_passed or attempts_failed == 0:
        independence = 100.0
        rationale.append("首次提交即通过，独立完成度很高。")
    else:
        independence = _clamp(100.0 - attempts_failed * 15.0, 20.0, 100.0)
        rationale.append(
            f"经历 {attempts_failed} 次失败后通过，独立性评分为 {round(independence)}。"
        )

    # ---- 维度 2：效率 ----
    # 以难度基准耗时为 1.0 倍速；比基准快不加分上限 100，慢则线性衰减
    baseline = _baseline_ms(evidence.difficulty)
    if evidence.time_spent_ms <= 0:
        efficiency = 60.0 if evidence.passed else 0.0
        if evidence.passed:
            rationale.append("未记录耗时，效率按中性值计。")
    else:
        ratio = evidence.time_spent_ms / baseline
        if ratio <= 1.0:
            efficiency = 100.0
        else:
            efficiency = _clamp(100.0 - (ratio - 1.0) * 50.0, 10.0, 100.0)
        if evidence.passed:
            minutes = round(evidence.time_spent_ms / 60000, 1)
            rationale.append(f"累计解题耗时 {minutes} 分钟（基准 {baseline // 60000} 分钟）。")
        else:
            efficiency = 0.0

    # ---- 维度 3：自主性 ----
    # 求助最多扣到 50 分，避免把「问导师」变成扣分重灾区（鼓励提问，但区分独立完成）
    hints = max(0, evidence.hints_used)
    self_reliance = _clamp(100.0 - hints * 10.0, 50.0, 100.0)
    if hints > 0:
        rationale.append(f"过程中使用了 {hints} 次 AI 伴学诊断。")

    # ---- 维度 4：完成度 ----
    completion = 100.0 if evidence.passed else 0.0
    if not evidence.passed:
        rationale.append("关卡未通过，完成度不计分。")

    score = (
        independence * _WEIGHT_INDEPENDENCE
        + efficiency * _WEIGHT_EFFICIENCY
        + self_reliance * _WEIGHT_SELF_RELIANCE
        + completion * _WEIGHT_COMPLETION
    )
    score = _clamp(score)

    # ---- 等级映射 ----
    if not evidence.passed:
        level = "D"
    elif score >= 90:
        level = "A"
    elif score >= 80:
        level = "B"
    elif score >= 65:
        level = "C"
    else:
        level = "D"

    # ---- 薄弱点提示（供导师与复习建议使用）----
    if evidence.failure_kinds:
        labels = []
        for kind in dict.fromkeys(evidence.failure_kinds):  # 去重且保序
            label = failure_kind_label(kind)
            if label not in labels:
                labels.append(label)
        rationale.append("过程中暴露的薄弱点：" + "、".join(labels) + "。")

    return MasteryResult(
        score=score,
        level=level,
        dimensions={
            "independence": independence,
            "efficiency": efficiency,
            "self_reliance": self_reliance,
            "completion": completion,
        },
        rationale=rationale,
    )


# ---------------------------------------------------------------------------
# 三、概念级掌握度画像（跨会话长期记忆）
# ---------------------------------------------------------------------------

def extract_concepts(phase_id: str, phase_title: str = "", tags: Optional[List[str]] = None) -> List[str]:
    """从关卡元数据中提取用于画像跟踪的概念标签。

    目前采用轻量规则：优先使用显式 tags，其次从标题与编号派生。
    后续可替换为更精细的概念图谱，调用方无需改动。
    """
    concepts: List[str] = []
    for tag in tags or []:
        cleaned = str(tag).strip()
        if cleaned and cleaned not in concepts:
            concepts.append(cleaned)

    if phase_title:
        cleaned = phase_title.strip()
        if cleaned and cleaned not in concepts:
            concepts.append(cleaned)

    if phase_id:
        cleaned = str(phase_id).strip()
        if cleaned and cleaned not in concepts:
            concepts.append(cleaned)

    return concepts


def update_concept_mastery(
    current_mastery: float,
    encounters: int,
    failures: int,
) -> float:
    """按遭遇次数与失败次数增量更新单个概念的掌握度（0-100）。

    采用指数滑动平均：新证据占比随遭遇次数增加而递减，保证画像稳定且能纠偏。
    """
    encounters = max(1, encounters)
    observed = _clamp(100.0 - (failures / encounters) * 100.0)
    alpha = max(0.25, 1.0 / encounters) if encounters > 1 else 1.0
    updated = current_mastery * (1 - alpha) + observed * alpha
    return _clamp(updated)


def now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)