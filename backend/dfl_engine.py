"""
DFL 语义增强中枢 (Dynamic Fusion Layer & Decision-Focused Feedback Loop)
核心目标:
1. Dynamic Fusion Layer (动态特征融合层):
   根据输入查询的语义特征（实体密度、信息熵、关键词结构、抽象度），
   自适应动态计算 Dense 向量(BGE-M3) 与 Sparse 稀疏(BM25) 的最优融合权重，替代静态固化权重。
2. Decision-Focused Feedback Loop (决策导向反馈闭环):
   以最终行动与执行决策为导向，提取结构化意图槽位，计算语义置信度。
   当置信度低于安全阈值时，自动触发主动澄清与反思反馈回路，避免语义歧义。
"""

import math
import re
from typing import Dict, Any, List, Tuple
from langchain_core.documents import Document


class DFLFusionLayer:
    """动态特征融合层 (Dynamic Fusion Layer)"""

    # 典型精确匹配特征模式（工单号、代码标识符、文件路径、标准专业术语）
    EXACT_PATTERNS = [
        r"[a-zA-Z0-9_-]{4,}",             # 字母数字复合代码/ID
        r"\b(api|http|ws|sql|rag|mcp|dfl|vllm|lora|kv)\b",
        r"\.[a-zA-Z0-9]{1,5}\b",          # 扩展名如 .py, .pdf, .json
        r"\d{4,}",                        # 长数字/年份/编号
        r"[“\"'「](.*?)[”\"'」]",           # 引号强引用专有名词
    ]

    def __init__(self, base_dense: float = 0.5, base_sparse: float = 0.5):
        self.base_dense = base_dense
        self.base_sparse = base_sparse

    def calculate_dynamic_weights(self, query: str) -> Tuple[float, float, Dict[str, Any]]:
        """
        根据 Query 的语言结构与语义特征动态计算 Dense 与 Sparse 权重。
        返回: (dense_weight, sparse_weight, feature_analysis)
        """
        query_strip = query.strip()
        length = len(query_strip)

        if length == 0:
            return self.base_dense, self.base_sparse, {"reason": "empty_query"}

        # 1. 专有名词与精确符号密度检测
        exact_matches = 0
        for pattern in self.EXACT_PATTERNS:
            exact_matches += len(re.findall(pattern, query_strip, re.IGNORECASE))

        # 2. 问询词与推理导向词检测（倾向高维语义理解）
        reasoning_keywords = [
            "为什么", "如何", "怎么理解", "分析", "区别", "原理", "对比", "解释",
            "架构", "设计模式", "总结", "综述", "优缺点", "核心价值"
        ]
        reasoning_score = sum(1 for kw in reasoning_keywords if kw in query_strip)

        # 3. 计算字词信息熵估计 (Shannon Entropy)
        char_freq = {}
        for ch in query_strip:
            char_freq[ch] = char_freq.get(ch, 0) + 1
        entropy = -sum((cnt / length) * math.log2(cnt / length) for cnt in char_freq.values())

        # 4. 动态门控融合权重算法 (Dynamic Gated Softmax)
        # 基础倾向: 短词/ID/明确符号倾向 Sparse (BM25)，长句/解释/高熵概念倾向 Dense
        sparse_bias = (exact_matches * 0.18) + (0.15 if length < 8 else 0.0)
        dense_bias = (reasoning_score * 0.20) + (0.15 if length > 25 else 0.0) + (entropy * 0.03)

        # 门控调节
        raw_sparse = self.base_sparse + sparse_bias - (dense_bias * 0.5)
        raw_dense = self.base_dense + dense_bias - (sparse_bias * 0.5)

        # 约束在 [0.15, 0.85] 之间，防止单边失真
        raw_sparse = max(0.15, min(0.85, raw_sparse))
        raw_dense = max(0.15, min(0.85, raw_dense))

        # 归一化
        total = raw_sparse + raw_dense
        final_dense = round(raw_dense / total, 3)
        final_sparse = round(raw_sparse / total, 3)

        diagnostics = {
            "query_length": length,
            "exact_matches": exact_matches,
            "reasoning_score": reasoning_score,
            "entropy": round(entropy, 2),
            "dynamic_dense_weight": final_dense,
            "dynamic_sparse_weight": final_sparse,
        }

        return final_dense, final_sparse, diagnostics

    def fuse_and_rerank(
        self,
        dense_docs: List[Tuple[Document, float]],
        sparse_docs: List[Tuple[Document, float]],
        dense_weight: float,
        sparse_weight: float,
        top_k: int = 4
    ) -> List[Document]:
        """
        将 Dense (相似度) 与 Sparse (BM25 分数) 通过 RRF (Reciprocal Rank Fusion) + DFL 动态加权合并
        """
        doc_scores: Dict[str, Dict[str, Any]] = {}
        rrf_k = 60.0  # RRF 常数

        # 累积 Dense 排名分数
        for rank, (doc, _) in enumerate(dense_docs):
            key = doc.page_content.strip()
            if key not in doc_scores:
                doc_scores[key] = {"doc": doc, "score": 0.0}
            doc_scores[key]["score"] += dense_weight * (1.0 / (rrf_k + rank + 1))

        # 累积 Sparse 排名分数
        for rank, (doc, _) in enumerate(sparse_docs):
            key = doc.page_content.strip()
            if key not in doc_scores:
                doc_scores[key] = {"doc": doc, "score": 0.0}
            doc_scores[key]["score"] += sparse_weight * (1.0 / (rrf_k + rank + 1))

        # 排序并提取 top_k
        sorted_docs = sorted(doc_scores.values(), key=lambda x: x["score"], reverse=True)
        return [item["doc"] for item in sorted_docs[:top_k]]


class DFLDecisionFeedback:
    """决策焦点学习与反思反馈闭环 (Decision-Focused Feedback Loop)"""

    CONFIDENCE_THRESHOLD = 0.65

    @classmethod
    def evaluate_intent(cls, user_prompt: str, context_summary: str = "") -> Dict[str, Any]:
        """
        对用户意图进行决策焦点分析：
        评估操作意向（只读/写/高危）、槽位完整性与置信度。
        """
        p = user_prompt.strip()
        length = len(p)

        # 1. 意图模糊度指标计算
        is_too_short = length < 3
        has_pronoun_ambiguity = bool(re.search(r"^(那个|这一个|帮我弄一下|那个问题|搞一下)$", p))

        # 2. 行为动作判别
        high_risk_actions = ["删除", "销毁", "重置", "清空", "修改密码", "DROP", "DELETE", "TRUNCATE"]
        query_actions = ["查询", "列出", "统计", "分析", "查看", "检索", "总结", "介绍", "什么是"]

        has_high_risk = any(act.lower() in p.lower() for act in high_risk_actions)
        has_query = any(act in p for act in query_actions)

        # 3. 计算置信度 (0.0 ~ 1.0)
        confidence = 0.85
        if is_too_short:
            confidence -= 0.45
        if has_pronoun_ambiguity:
            confidence -= 0.40
        if not has_query and not has_high_risk and length < 10:
            confidence -= 0.20

        confidence = max(0.1, min(1.0, round(confidence, 2)))
        needs_clarification = confidence < cls.CONFIDENCE_THRESHOLD

        clarification_prompt = None
        if needs_clarification:
            if is_too_short or has_pronoun_ambiguity:
                clarification_prompt = "请问您具体指的是哪一份文档、系统模块或具体的业务数据？提供更多关键词我能为您精准定位。"
            else:
                clarification_prompt = "您的需求有多种理解方向，请问您是希望进行【业务数据查询】还是【系统功能配置】？"

        return {
            "prompt": user_prompt,
            "confidence": confidence,
            "is_high_risk": has_high_risk,
            "needs_clarification": needs_clarification,
            "clarification_prompt": clarification_prompt,
            "decision_target": "HIGH_RISK_ACTION" if has_high_risk else ("QUERY_ACTION" if has_query else "GENERAL_CHAT")
        }


# 全局单例导出
dfl_fusion = DFLFusionLayer()
dfl_feedback = DFLDecisionFeedback()
