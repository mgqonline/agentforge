import os
import json
import unittest
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, engine
from sample_data import SAMPLE_DOCUMENTS


class TestHybridRAG(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """确保测试前有初始示例文档与引擎实例"""
        import app as app_module
        if app_module.engine is None:
            from rag_engine import HybridRAGEngine
            app_module.engine = HybridRAGEngine()
        
        cls.engine = app_module.engine
        if cls.engine.get_doc_count() == 0:
            cls.engine.add_documents(SAMPLE_DOCUMENTS)
        cls.client = TestClient(app)


    def test_status_endpoint(self):
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "running")
        self.assertGreater(data["doc_count"], 0)

    def test_chat_stream_session_isolation_and_params(self):
        # 测试 Session A
        payload_a = {
            "session_id": "session_test_a",
            "query": "什么是向量检索？",
            "use_rag": True,
            "top_k": 3
        }
        response_a = self.client.post("/api/v1/chat/stream", json=payload_a)
        self.assertEqual(response_a.status_code, 200)
        self.assertIn("data:", response_a.text)
        self.assertIn("session_test_a", self.engine.sessions)
        self.assertGreater(len(self.engine.sessions["session_test_a"]), 0)

        # 测试 Session B (关闭 RAG)
        payload_b = {
            "session_id": "session_test_b",
            "query": "你好，请介绍一下你自己",
            "use_rag": False,
            "top_k": 5
        }
        response_b = self.client.post("/api/v1/chat/stream", json=payload_b)
        self.assertEqual(response_b.status_code, 200)
        self.assertIn("session_test_b", self.engine.sessions)
        # 验证 Session A 与 Session B 隔离
        self.assertNotEqual(self.engine.sessions["session_test_a"], self.engine.sessions["session_test_b"])


    def test_search_endpoint(self):
        response = self.client.post("/api/search", json={"query": "BM25", "top_k": 3})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertLessEqual(len(data["reranked_results"]), 3)

if __name__ == "__main__":
    unittest.main()

