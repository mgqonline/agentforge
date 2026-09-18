"""
26-hybrid-search-rerank: 工业级混合检索与交叉编码器重排系统 (Hybrid Search & RRF & Reranker)
-----------------------------------------------------------------------------------------
本模块解决纯向量 Dense 检索在专业领域、特定型号与专有名词上命中率低下 (常见低于 60%) 的工业界通病。

核心管线:
1. BM25 稀疏词法检索 (Sparse Keyword Retrieval) -> 精准捕获代码名、型号、错误码;
2. Dense 稠密语义向量检索 (Dense Semantic Retrieval) -> 泛化捕获同义表述与语义意图;
3. 倒排倒数融合算法 (RRF, Reciprocal Rank Fusion) -> 无量纲差异的排位融合;
4. 交叉编码器深度重排 (Cross-Encoder / Reranker) -> 将 Top-N 候选段落进行二次深度注意力对齐打分。
"""

import math
import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class Document:
    doc_id: str
    title: str
    content: str
    keywords: List[str]


# -------------------------------------------------------------
# 1. 轻量高效纯 Python 实现的 BM25 词法检索引擎
# -------------------------------------------------------------
class SimpleBM25:
    def __init__(self, docs: List[Document], k1: float = 1.5, b: float = 0.75):
        self.docs = docs
        self.k1 = k1
        self.b = b
        self.corpus_size = len(docs)
        self.doc_lens = [len(self.tokenize(d.content)) for d in docs]
        self.avg_doc_len = sum(self.doc_lens) / max(1, self.corpus_size)
        self.doc_freqs: Dict[str, int] = {}
        self.doc_term_counts: List[Dict[str, int]] = []
        
        for d in docs:
            tokens = self.tokenize(d.content)
            counts: Dict[str, int] = {}
            for t in tokens:
                counts[t] = counts.get(t, 0) + 1
            self.doc_term_counts.append(counts)
            for t in set(tokens):
                self.doc_freqs[t] = self.doc_freqs.get(t, 0) + 1

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """中英文分词器 (支持专有名词与字母数字混合 token)"""
        # 提取英文与数字
        tokens = re.findall(r"[a-zA-Z0-9_-]+|[\u4e00-\u9fa5]", text.lower())
        return tokens

    def score(self, query: str) -> List[Tuple[str, float]]:
        q_tokens = self.tokenize(query)
        scores = []
        for idx, d in enumerate(self.docs):
            doc_score = 0.0
            doc_len = self.doc_lens[idx]
            counts = self.doc_term_counts[idx]
            for t in q_tokens:
                if t not in counts:
                    continue
                tf = counts[t]
                df = self.doc_freqs.get(t, 0)
                # IDF 计算
                idf = math.log((self.corpus_size - df + 0.5) / (df + 0.5) + 1.0)
                # BM25 长度正则项
                denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                term_score = idf * ((tf * (self.k1 + 1.0)) / max(1e-6, denom))
                doc_score += term_score
            scores.append((d.doc_id, round(doc_score, 4)))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores


# -------------------------------------------------------------
# 2. 模拟 Dense 语义向量检索 (基于哈希空间高维投影与语义意图)
# -------------------------------------------------------------
class MockDenseEmbeddingRetriever:
    """模拟真实向量库 (如 Chroma / BGE-M3 / OpenAI text-embedding-3)"""
    def __init__(self, docs: List[Document]):
        self.docs = docs

    def _pseudo_embed(self, text: str) -> List[float]:
        """生成一个稳定的 16 维确定性伪向量用于无外部大依赖的离线沙箱运行"""
        dim = 16
        vec = [0.0] * dim
        tokens = re.findall(r"[a-zA-Z0-9]+|[\u4e00-\u9fa5]", text.lower())
        for i, tok in enumerate(tokens):
            h = hash(tok)
            vec[h % dim] += 1.0 / (1.0 + i * 0.1)
        # L2 归一化
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [round(x / norm, 4) for x in vec]

    def score(self, query: str) -> List[Tuple[str, float]]:
        q_vec = self._pseudo_embed(query)
        results = []
        for d in self.docs:
            d_vec = self._pseudo_embed(d.title + " " + d.content)
            # 余弦相似度
            sim = sum(a * b for a, b in zip(q_vec, d_vec))
            results.append((d.doc_id, round(sim, 4)))
        results.sort(key=lambda x: x[1], reverse=True)
        return results


# -------------------------------------------------------------
# 3. 倒排倒数融合算法 (RRF, Reciprocal Rank Fusion)
# -------------------------------------------------------------
def reciprocal_rank_fusion(
    ranked_lists: List[List[Tuple[str, float]]],
    k: int = 60
) -> List[Tuple[str, float]]:
    """
    RRF 算法公式: Score(d) = sum_{m in models} 1 / (k + rank_m(d))
    k 为平滑常数 (工业界标准通常取 60)
    优点: 无需对不同维度的分数做 Min-Max 归一化，排位鲁棒性极高
    """
    rrf_scores: Dict[str, float] = {}
    for r_list in ranked_lists:
        for rank, (doc_id, _) in enumerate(r_list, 1):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            
    sorted_rrf = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return [(doc_id, round(score, 6)) for doc_id, score in sorted_rrf]


# -------------------------------------------------------------
# 4. 交叉编码器二次深度重排器 (Cross-Encoder / Reranker)
# -------------------------------------------------------------
class CrossEncoderReranker:
    """
    Cross-Encoder 不像 Bi-Encoder 将 Query 和 Doc 分开独立向量化，
    而是将 (Query, Doc) 拼接到一起通过全注意力层计算交互打分，精度显著超越 Bi-Encoder。
    """
    def rerank(
        self,
        query: str,
        candidate_ids: List[str],
        docs_map: Dict[str, Document]
    ) -> List[Dict[str, Any]]:
        results = []
        q_tokens = set(re.findall(r"[a-zA-Z0-9]+|[\u4e00-\u9fa5]", query.lower()))
        
        for doc_id in candidate_ids:
            doc = docs_map.get(doc_id)
            if not doc:
                continue
            
            d_tokens = set(re.findall(r"[a-zA-Z0-9]+|[\u4e00-\u9fa5]", (doc.title + " " + doc.content).lower()))
            common_overlap = len(q_tokens.intersection(d_tokens)) / max(1, len(q_tokens))
            
            # 模拟 Cross-Encoder 对关键实体/核心结论的精准注意力交互打分
            keyword_hit = sum(1 for kw in doc.keywords if kw.lower() in query.lower())
            
            relevance = 0.5 * common_overlap + 0.5 * (min(1.0, keyword_hit * 0.4))
            results.append({
                "doc_id": doc.doc_id,
                "title": doc.title,
                "relevance_score": round(relevance, 4),
                "content_snippet": doc.content[:80] + "..."
            })
            
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results


# -------------------------------------------------------------
# 5. 端到端完整混合检索流水线执行
# -------------------------------------------------------------
def run_hybrid_search_pipeline() -> Dict[str, Any]:
    # 模拟企业冷链与高并发技术真实知识库语料
    corpus = [
        Document(
            doc_id="DOC_001",
            title="冷链温控车载传感器 ERR_TEMP_4091 硬件故障手册",
            content="当冷链冷藏车在高速行驶时，温控传感器可能出现 ERR_TEMP_4091 代码。该错误由于车载通信总线在颠簸中信号瞬时阻抗不稳引起，需重启传感器并检查物理连接。",
            keywords=["ERR_TEMP_4091", "传感器", "冷链", "冷藏车"]
        ),
        Document(
            doc_id="DOC_002",
            title="大模型 API 网关流式 SSE 与分布式任务调度设计",
            content="FastAPI 网关结合 Server-Sent Events (SSE) 可以为用户提供丝滑打字机体验，后台使用 Celery 实现任务削峰填谷，降低高并发长耗时请求的拥堵风险。",
            keywords=["FastAPI", "SSE", "Celery", "网关"]
        ),
        Document(
            doc_id="DOC_003",
            title="生鲜果蔬运输中的恒温保鲜与仓储冷链规范",
            content="为保障车厘子、蓝莓等高价值水果的新鲜度，仓储冷链必须保持在 2℃ 至 4℃ 的恒温环境，并实时监测湿度在 85% 以上。",
            keywords=["保鲜", "冷链", "水果", "仓储"]
        ),
        Document(
            doc_id="DOC_004",
            title="智能调度中心：货运物流车辆故障排查与远程救援指南",
            content="针对途中货车报障，智能调度系统会根据车牌号定位就近维修服务站，若遇到电气与通信总线故障，先执行电气隔离测试。",
            keywords=["调度", "排查", "货运", "电气"]
        )
    ]
    docs_map = {d.doc_id: d for d in corpus}

    bm25 = SimpleBM25(corpus)
    dense = MockDenseEmbeddingRetriever(corpus)
    reranker = CrossEncoderReranker()

    # 复杂用户查询：包含精确专有错误代码与语义描述
    query = "冷链车在路上报 ERR_TEMP_4091 故障怎么快速处理？"

    print("=" * 75)
    print("🔍 [Hybrid RAG] 工业级混合检索与重排全流程演示")
    print(f"🎯 用户查询: \"{query}\"")
    print("=" * 75)

    # 1. 稀疏检索 (BM25)
    bm25_res = bm25.score(query)
    print("\n[Step 1: BM25 词法检索 Top 3]")
    for rank, (doc_id, score) in enumerate(bm25_res[:3], 1):
        print(f"  #{rank} [{doc_id}] 得分: {score} | {docs_map[doc_id].title}")

    # 2. 稠密检索 (Dense)
    dense_res = dense.score(query)
    print("\n[Step 2: Dense 语义向量检索 Top 3]")
    for rank, (doc_id, score) in enumerate(dense_res[:3], 1):
        print(f"  #{rank} [{doc_id}] 得分: {score} | {docs_map[doc_id].title}")

    # 3. 倒排倒数融合 (RRF)
    rrf_res = reciprocal_rank_fusion([bm25_res, dense_res], k=60)
    print("\n[Step 3: RRF 融合打分 (Top 3 候选集)]")
    candidate_ids = [doc_id for doc_id, _ in rrf_res[:3]]
    for rank, (doc_id, rrf_score) in enumerate(rrf_res[:3], 1):
        print(f"  #{rank} [{doc_id}] RRF Score: {rrf_score:.6f} | {docs_map[doc_id].title}")

    # 4. Cross-Encoder 深度二次重排
    final_ranked = reranker.rerank(query, candidate_ids, docs_map)
    print("\n[Step 4: Cross-Encoder 精准重排最终交付 LLM 的上下文]")
    for rank, item in enumerate(final_ranked, 1):
        print(f"  🏆 最终第 {rank} 名: [{item['doc_id']}] 关联度: {item['relevance_score']:.4f}")
        print(f"     标题: {item['title']}")
        print(f"     摘要: {item['content_snippet']}\n")

    return {
        "status": "success",
        "top_doc": final_ranked[0]["doc_id"],
        "top_score": final_ranked[0]["relevance_score"]
    }


if __name__ == "__main__":
    run_hybrid_search_pipeline()
