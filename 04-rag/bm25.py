import math
from collections import Counter

class BM25:
    def __init__(self, corpus: list[list[str]], k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.N = len(corpus)
        self.avgdl = sum(len(doc) for doc in corpus) / self.N
        self.doc_freqs = [Counter(doc) for doc in corpus]
        self.idf = self._compute_idf()

    def _compute_idf(self) -> dict:
        idf = {}
        all_terms = set(term for doc in self.corpus for term in doc)
        for term in all_terms:
            n_q = sum(1 for doc in self.corpus if term in doc)
            idf[term] = math.log((self.N - n_q + 0.5) / (n_q + 0.5) + 1)
        return idf

    def score(self, query: list[str], doc_idx: int) -> float:
        doc = self.corpus[doc_idx]
        doc_len = len(doc)
        tf = self.doc_freqs[doc_idx]
        score = 0.0

        for term in query:
            if term not in tf:
                continue
            f = tf[term]
            idf = self.idf.get(term, 0)
            numerator = f * (self.k1 + 1)
            denominator = f + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
            score += idf * numerator / denominator

        return score

    def rank(self, query: list[str]) -> list[tuple[int, float]]:
        scores = [(i, self.score(query, i)) for i in range(self.N)]
        return sorted(scores, key=lambda x: x[1], reverse=True)


# ── 示例 ──────────────────────────────────────────────────────────────
corpus = [
    "冷链运输 温控 货物 长沙 娄底".split(),
    "冷链 仓储 温控 新鲜 蔬菜 水果".split(),
    "道路运输 货物 调度 司机 车辆".split(),
    "冷链 温控 设备 监控 传感器".split(),
]

bm25 = BM25(corpus)
query = "冷链 温控".split()
results = bm25.rank(query)

for rank, (idx, score) in enumerate(results, 1):
    print(f"第{rank}名  文档{idx}  得分={score:.4f}  内容={corpus[idx]}")