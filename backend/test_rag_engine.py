import unittest
import os
import sys

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rag_engine import RAGEngine

class TestRAGEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RAGEngine()

    def test_rag_engine_initialization(self):
        self.assertIsNotNone(self.engine)
        self.assertTrue(hasattr(self.engine, 'build_or_load'))

    def test_rag_engine_retrieve(self):
        context, sources = self.engine.retrieve("拓维信息", k=1)
        self.assertIsInstance(context, str)
        self.assertIsInstance(sources, list)

if __name__ == '__main__':
    unittest.main()
