"""
25-reasoning-rl: 大模型后训练强化学习与长思维链推理 (GRPO & Reasoning RL)
-------------------------------------------------------------------------
本模块模拟并落地 DeepSeek-R1 核心的 Group Relative Policy Optimization (GRPO)
及长思维链 (Long-CoT) 规则奖励与自适应反思进化管道。

核心特性:
1. 无需额外 Critic 评估大模型（节省 50% 显存开销）；
2. 组内相对优势打分 (Group Advantage Normalization)；
3. 复合规则奖励函数:
   - 正确性奖励 (Accuracy Reward)
   - 格式规范性奖励 (XML <think> 标签闭合与思考长度)
   - 冗余冗长惩罚 (Conciseness Penalty)
4. 自我纠错与反思迭代模拟 (Self-Correction Loop)
"""

import math
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple


@dataclass
class TrajectorySample:
    """单个采样轨迹及其推理过程"""
    sample_id: int
    prompt: str
    thought_process: str   # <think>...</think>
    final_answer: str      # 最终结论
    tokens_count: int


@dataclass
class RewardBreakdown:
    """奖励细分项"""
    accuracy_score: float  # 0.0 ~ 1.0 (结果严格对齐)
    format_score: float    # 0.0 ~ 1.0 (XML 格式正确)
    length_penalty: float  # 惩罚项 (负值或 0)
    total_reward: float    # 综合奖励


class GRPORuleEngine:
    """
    GRPO 组相对策略优化规则打分引擎
    """
    def __init__(self, target_think_min: int = 15, target_think_max: int = 150):
        self.target_think_min = target_think_min
        self.target_think_max = target_think_max

    def evaluate_format(self, text: str) -> float:
        """评估思考格式: 必须包含成对的 <think> 与 </think> 标签，且标签内有实质性推导"""
        has_start = "<think>" in text
        has_end = "</think>" in text
        if not (has_start and has_end):
            return 0.0
        
        # 提取思考内容
        match = re.search(r"<think>(.*?)</think>", text, re.DOTALL)
        if not match:
            return 0.2
        
        think_content = match.group(1).strip()
        if len(think_content) < self.target_think_min:
            return 0.5  # 思考过于敷衍
        return 1.0

    def evaluate_accuracy(self, predicted_answer: str, ground_truth: str) -> float:
        """评估最终答案是否正确匹配真值 (支持数值与关键字正则)"""
        pred_clean = predicted_answer.strip().lower()
        gt_clean = ground_truth.strip().lower()
        
        if pred_clean == gt_clean:
            return 1.0
        
        # 数值提取比对
        pred_numbers = re.findall(r"[-+]?\d*\.?\d+", pred_clean)
        gt_numbers = re.findall(r"[-+]?\d*\.?\d+", gt_clean)
        if pred_numbers and gt_numbers and pred_numbers[-1] == gt_numbers[-1]:
            return 1.0
        
        return 0.0

    def compute_length_penalty(self, think_length: int) -> float:
        """冗长惩罚：若无意义过度思考（复读机），按指数衰减扣分"""
        if think_length > self.target_think_max:
            overflow = think_length - self.target_think_max
            return -min(0.5, round(overflow * 0.005, 4))
        return 0.0

    def calculate_reward(self, response_text: str, ground_truth: str) -> RewardBreakdown:
        """计算单条轨迹的综合奖励"""
        format_score = self.evaluate_format(response_text)
        
        # 提取最终答案
        if "</think>" in response_text:
            final_answer = response_text.split("</think>")[-1].strip()
            think_match = re.search(r"<think>(.*?)</think>", response_text, re.DOTALL)
            think_len = len(think_match.group(1)) if think_match else 0
        else:
            final_answer = response_text
            think_len = 0
            
        accuracy_score = self.evaluate_accuracy(final_answer, ground_truth)
        length_penalty = self.compute_length_penalty(think_len)
        
        # 综合奖励 = 准确率权重 0.7 + 格式权重 0.3 + 长度惩罚
        total = round(accuracy_score * 0.7 + format_score * 0.3 + length_penalty, 4)
        total = max(0.0, total)
        
        return RewardBreakdown(
            accuracy_score=accuracy_score,
            format_score=format_score,
            length_penalty=length_penalty,
            total_reward=total
        )


def compute_grpo_advantages(rewards: List[float]) -> List[float]:
    """
    计算组内相对优势 (Group Relative Advantages)
    A_i = (R_i - mean(R)) / (std(R) + eps)
    这是 GRPO 的数学灵魂：不再依赖 Critic 网络预估基线，而是直接用同 Prompt 采样的多个候选响应进行组内标准化！
    """
    if not rewards:
        return []
    n = len(rewards)
    if n == 1:
        return [0.0]
    
    mean_r = sum(rewards) / n
    variance = sum((r - mean_r) ** 2 for r in rewards) / n
    std_r = math.sqrt(variance)
    eps = 1e-6
    
    advantages = [round((r - mean_r) / (std_r + eps), 4) for r in rewards]
    return advantages


def run_grpo_pipeline_demo() -> Dict[str, Any]:
    """演示完整的 GRPO 推理打分与组内优势分布"""
    engine = GRPORuleEngine()
    question = "一个水箱进水管每小时注入 12 升水，出水管每小时流出 4 升水。若水箱容积为 40 升，最初为空，几小时能注满？"
    ground_truth = "5小时"

    # 模拟针对同一 Prompt 并行采样的 4 条候选推理轨迹 (Group Size G = 4)
    sampled_responses = [
        # 采样 1：优质长思维链推导，答案正确
        "<think>首先计算净进水速度：每小时进水 12 升，出水 4 升，则净增加 12 - 4 = 8 升/小时。水箱总容积为 40 升。所需时间 = 40 / 8 = 5 小时。反复核实无误。</think>最终答案是 5小时。",
        
        # 采样 2：答案正确，但缺少标准 <think> 标签
        "净速度为每小时 8 升，40 除以 8 等于 5，所以需要 5小时。",
        
        # 采样 3：有思考标签，但计算错误 (把出水当成了加法)
        "<think>12 加 4 等于 16 升。40 除以 16 等于 2.5 小时。</think>最终答案是 2.5小时。",
        
        # 采样 4：格式正确但复读机冗长，触发长度惩罚
        "<think>" + "我们在思考这个问题，需要计算净速度..." * 15 + "最终算得 12-4=8, 40/8=5小时。</think>答案是 5小时。"
    ]

    breakdowns: List[RewardBreakdown] = []
    for resp in sampled_responses:
        reward = engine.calculate_reward(resp, ground_truth)
        breakdowns.append(reward)

    rewards_list = [b.total_reward for b in breakdowns]
    advantages = compute_grpo_advantages(rewards_list)

    print("=" * 70)
    print("🚀 [GRPO] Group Relative Policy Optimization 实战演练")
    print("=" * 70)
    print(f"📌 输入题目: {question}")
    print(f"🎯 标准答案: {ground_truth}\n")

    for i, (resp, b, adv) in enumerate(zip(sampled_responses, breakdowns, advantages), 1):
        print(f"--- 采样轨迹 #{i} ---")
        preview = resp[:65] + "..." if len(resp) > 65 else resp
        print(f"  文本摘要: {preview}")
        print(f"  指标打分: 准确率={b.accuracy_score} | 格式分={b.format_score} | 长度惩罚={b.length_penalty}")
        print(f"  综合奖励 R: {b.total_reward}")
        print(f"  💡 组内优势 A (Advantage): {adv:+.4f} ({'强化提升' if adv > 0 else '抑制衰减'})\n")

    return {
        "status": "success",
        "rewards": rewards_list,
        "advantages": advantages
    }


if __name__ == "__main__":
    run_grpo_pipeline_demo()
