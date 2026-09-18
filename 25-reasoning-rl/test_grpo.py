import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from grpo_reasoning_pipeline import GRPORuleEngine, compute_grpo_advantages


class TestGRPORuleEngine(unittest.TestCase):
    def setUp(self):
        self.engine = GRPORuleEngine(target_think_min=10, target_think_max=100)

    def test_format_reward(self):
        # 1. 优质思考
        good = "<think>这是一段严谨的推导过程，首先A等于1，B等于2，因此和为3。</think>答案是3"
        self.assertEqual(self.engine.evaluate_format(good), 1.0)

        # 2. 缺少结束标签
        incomplete = "<think>推导中途截断"
        self.assertEqual(self.engine.evaluate_format(incomplete), 0.0)

        # 3. 思考过于简短
        too_short = "<think>算</think>答案是3"
        self.assertEqual(self.engine.evaluate_format(too_short), 0.5)

    def test_accuracy_reward(self):
        self.assertEqual(self.engine.evaluate_accuracy("5小时", "5小时"), 1.0)
        self.assertEqual(self.engine.evaluate_accuracy("最终计算得到 5 小时整", "5小时"), 1.0)
        self.assertEqual(self.engine.evaluate_accuracy("答案是 3 小时", "5小时"), 0.0)

    def test_grpo_advantages(self):
        rewards = [1.0, 0.7, 0.3, 0.5]
        advantages = compute_grpo_advantages(rewards)
        self.assertEqual(len(advantages), 4)
        
        # 最好的一条优势必须大于 0
        self.assertGreater(advantages[0], 0)
        # 最差的一条优势必须小于 0
        self.assertLess(advantages[2], 0)
        # 优势之和在标准化后应趋近于 0
        self.assertAlmostEqual(sum(advantages), 0.0, places=3)


if __name__ == "__main__":
    unittest.main()
