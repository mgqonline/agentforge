import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from hybrid_retriever_rerank import Document, SimpleBM25, reciprocal_rank_fusion, CrossEncoderReranker


class TestHybridSearch(unittest.TestCase):
    def setUp(self):
        self.corpus = [
            Document("D1", "冷链监控", "冷链传感器 ERR_TEMP_4091 故障", ["ERR_TEMP_4091", "冷链"]),
            Document("D2", "水果保鲜", "蓝莓保鲜冷藏温度 2 度", ["保鲜", "水果"]),
            Document("D3", "系统架构", "FastAPI 和 Celery 分布式任务调度", ["FastAPI", "Celery"])
        ]
        self.bm25 = SimpleBM25(self.corpus)
        self.docs_map = {d.doc_id: d for d in self.corpus}

    def test_bm25_exact_code_match(self):
        scores = self.bm25.score("ERR_TEMP_4091")
        self.assertEqual(scores[0][0], "D1", "BM25 应对专有错误码实现精确召回第一名")
        self.assertGreater(scores[0][1], 0.0)

    def test_rrf_ranking(self):
        # 列表 A: D1 第一，D2 第二
        list_a = [("D1", 10.0), ("D2", 5.0)]
        # 列表 B: D1 第一，D3 第二
        list_b = [("D1", 0.9), ("D3", 0.8)]
        
        rrf = reciprocal_rank_fusion([list_a, list_b], k=60)
        self.assertEqual(rrf[0][0], "D1", "在两个通道均排第一的文档在 RRF 中必须排第一")
        self.assertAlmostEqual(rrf[0][1], 1.0/61 + 1.0/61, places=5)

    def test_cross_encoder_rerank(self):
        reranker = CrossEncoderReranker()
        results = reranker.rerank("ERR_TEMP_4091 怎么解决", ["D2", "D1"], self.docs_map)
        self.assertEqual(results[0]["doc_id"], "D1", "Cross-Encoder 必须将高匹配实体文档重排为第一位")
        self.assertGreater(results[0]["relevance_score"], results[1]["relevance_score"])


if __name__ == "__main__":
    unittest.main()
