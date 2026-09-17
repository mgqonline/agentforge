"""
效果归因系统（Effect Attribution System）
目标：当线上 RAG/Agent 效果下降时，能快速定位是模型、Prompt、检索还是工具的问题

核心架构：在每个关键节点埋点 (Span)，记录输入输出和质量指标
"""

import time
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, Any
from enum import Enum


# ============================================================
# 1. 数据结构定义：统一的追踪节点 (Span)
# ============================================================
class SpanStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    DEGRADED = "degraded"   # 降级（成功但质量不达标）


@dataclass
class Span:
    """
    一个 Span 代表整个 RAG 链路中的一个节点
    类比：LangSmith / Jaeger 等追踪系统中的一个追踪单元
    """
    span_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    trace_id: str = ""
    name: str = ""
    status: SpanStatus = SpanStatus.SUCCESS
    latency_ms: float = 0.0

    # 输入输出 & 质量指标
    input: Any = None
    output: Any = None
    quality_score: Optional[float] = None  # 该节点的质量评分 (0~1)
    error_message: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        d = asdict(self)
        d["status"] = self.status.value
        return d


# ============================================================
# 2. 核心追踪器：为每个链路步骤生成 Span
# ============================================================
class RAGTracer:
    """轻量级 RAG 链路追踪器（生产中可替换为 LangSmith / Phoenix）"""

    def __init__(self, trace_id: str = None):
        self.trace_id = trace_id or str(uuid.uuid4())[:8]
        self.spans: list[Span] = []

    def start_span(self, name: str, input_data: Any = None) -> Span:
        span = Span(trace_id=self.trace_id, name=name, input=input_data)
        return span

    def end_span(self, span: Span, output: Any = None,
                 quality_score: float = None, error: str = None,
                 latency_ms: float = 0):
        span.output = output
        span.latency_ms = latency_ms
        if error:
            span.status = SpanStatus.FAILED
            span.error_message = error
        elif quality_score is not None and quality_score < 0.5:
            span.status = SpanStatus.DEGRADED
            span.quality_score = quality_score
        else:
            span.status = SpanStatus.SUCCESS
            span.quality_score = quality_score
        self.spans.append(span)
        return span

    def report(self):
        """打印完整的链路分析报告"""
        print(f"\n{'='*60}")
        print(f"🔍 Trace ID: {self.trace_id}  链路分析报告")
        print(f"{'='*60}")

        bottleneck = None
        min_score = 1.0

        for span in self.spans:
            icon = {"success": "✅", "failed": "❌", "degraded": "⚠️"}.get(span.status.value, "❓")
            score_str = f"质量分: {span.quality_score:.2f}" if span.quality_score is not None else ""
            latency_str = f"耗时: {span.latency_ms:.0f}ms"
            err_str = f"  ← 错误: {span.error_message}" if span.error_message else ""
            print(f"  {icon} [{span.name}]  {latency_str}  {score_str}{err_str}")

            # 记录质量最差的节点（瓶颈）
            if span.quality_score is not None and span.quality_score < min_score:
                min_score = span.quality_score
                bottleneck = span

        print(f"\n{'─'*60}")
        if any(s.status == SpanStatus.FAILED for s in self.spans):
            failed = [s for s in self.spans if s.status == SpanStatus.FAILED][0]
            print(f"🚨 [归因结论] 硬性失败！问题出在【{failed.name}】节点: {failed.error_message}")
        elif bottleneck and min_score < 0.7:
            print(f"📉 [归因结论] 质量降级！最大瓶颈在【{bottleneck.name}】节点 (分={min_score:.2f})")
            _print_suggestion(bottleneck.name)
        else:
            print("✨ [归因结论] 本次请求链路健康，各节点质量良好。")
        print(f"{'='*60}\n")


def _print_suggestion(bottleneck_name: str):
    """根据瓶颈节点给出优化建议"""
    suggestions = {
        "retrieval": (
            "🔧 【检索层问题】可能原因与行动项：\n"
            "  1. 检查检索到的 Top-K 文档与 Query 是否真正相关（召回率低）\n"
            "  2. 尝试混合检索（向量 + BM25 关键词），防止专有名词漏召回\n"
            "  3. 增加 Reranker 重排步骤，过滤掉低质量文档\n"
            "  4. 排查 Embedding 模型是否与业务数据的语义空间匹配"
        ),
        "prompt": (
            "🔧 【Prompt 层问题】可能原因与行动项：\n"
            "  1. 检查 Prompt 模板是否因近期改动导致结构变化（做版本 A/B 对比）\n"
            "  2. 检查是否有幻觉约束指令（如: 禁止编造不在上下文中的内容）\n"
            "  3. 尝试使用 DSPy Optimizer 自动重新优化 Prompt\n"
            "  4. 检查 Few-Shot 样例是否已经过时（业务场景已变化）"
        ),
        "llm_generation": (
            "🔧 【模型生成层问题】可能原因与行动项：\n"
            "  1. 检查大模型服务商是否有悄悄切换底层模型版本（查 API 日志）\n"
            "  2. 检查 Temperature、max_tokens 等参数是否被意外修改\n"
            "  3. 检查输入 Token 是否超过上下文窗口导致截断\n"
            "  4. 对比上线前后的模型版本，必要时锁定 model version"
        ),
        "tool_call": (
            "🔧 【工具调用层问题】可能原因与行动项：\n"
            "  1. 检查第三方 API 是否有接口变更或字段调整\n"
            "  2. 检查参数解析逻辑，大模型是否在传递格式异常的参数\n"
            "  3. 查看工具调用的超时率和错误码分布\n"
            "  4. 增加工具层的降级策略（fallback）"
        )
    }
    print(suggestions.get(bottleneck_name, "  请人工介入排查。"))


# ============================================================
# 3. 模拟一次完整的 RAG 请求（带全链路追踪）
# ============================================================

def mock_retrieval(query: str) -> tuple[list[str], float]:
    """模拟向量数据库检索，返回文档和召回质量分"""
    time.sleep(0.05)  # 模拟网络耗时
    if "不存在的知识" in query:
        # 模拟检索质量极差的场景
        return ["这是一段完全不相关的文档...", "另一段无关文档..."], 0.25
    return ["合同违约金按日0.05%计算", "违约方需在30天内赔偿"], 0.92


def mock_llm(prompt: str, docs: list) -> tuple[str, float]:
    """模拟大模型生成，返回回答和生成质量分"""
    time.sleep(0.1)  # 模拟推理耗时
    answer = f"根据知识库文档：{'；'.join(docs)}，因此违约金计算标准为每日0.05%。"
    return answer, 0.88


def run_rag_request(user_query: str):
    """执行一次带完整追踪的 RAG 请求"""
    print(f"\n📥 用户提问: {user_query}")
    tracer = RAGTracer()

    # ── 节点1: 检索层 ──────────────────────────────
    t0 = time.time()
    span_ret = tracer.start_span("retrieval", input_data=user_query)
    docs, ret_score = mock_retrieval(user_query)
    tracer.end_span(span_ret, output=docs, quality_score=ret_score,
                    latency_ms=(time.time() - t0) * 1000)

    # 如果检索质量不足，提前归因，不再继续浪费模型 Token
    if ret_score < 0.5:
        tracer.report()
        return

    # ── 节点2: Prompt 组装层 ────────────────────────
    t0 = time.time()
    span_prompt = tracer.start_span("prompt")
    prompt = f"请根据以下资料回答问题：\n{chr(10).join(docs)}\n问题：{user_query}"
    # 模拟 Prompt 质量检查（比如检查是否包含防幻觉指令）
    prompt_score = 0.95 if "请根据以下资料" in prompt else 0.40
    tracer.end_span(span_prompt, output=prompt, quality_score=prompt_score,
                    latency_ms=(time.time() - t0) * 1000)

    # ── 节点3: 大模型生成层 ─────────────────────────
    t0 = time.time()
    span_llm = tracer.start_span("llm_generation")
    try:
        answer, gen_score = mock_llm(prompt, docs)
        tracer.end_span(span_llm, output=answer, quality_score=gen_score,
                        latency_ms=(time.time() - t0) * 1000)
    except Exception as e:
        tracer.end_span(span_llm, error=str(e),
                        latency_ms=(time.time() - t0) * 1000)
        tracer.report()
        return

    # 打印最终结论
    tracer.report()
    print(f"💬 最终回答: {answer}")


# ============================================================
# 4. 场景演示
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("场景 1：正常请求（所有节点健康）")
    print("=" * 60)
    run_rag_request("合同违约金怎么计算？")

    print("\n" + "=" * 60)
    print("场景 2：检索层异常（召回文档与问题无关）")
    print("=" * 60)
    run_rag_request("这是一个不存在的知识请求")
