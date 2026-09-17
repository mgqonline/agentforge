"""
第十二课：解码策略 (Decoding Strategies) —— 决定 AI 的表现力
============================================================
业务痛点：
  大模型最后一层输出的是词表中所有词的概率分布（比如 10万个词每个词的概率）。
  我们如何从中挑出“下一个词”？
  - 每次都挑概率最大的？（AI 变得像复读机，极其死板）
  - 每次都按概率随机抽？（AI 变得像疯子，胡言乱语）

核心策略：Temperature, Top-K, Top-P 的魔法
  这就是为什么在 API 调用时，调整这些参数能让 AI 在“严谨的程序员”和“发散的小说家”之间切换。

本课目标：
  直观感受这三个参数是如何改变概率分布，进而改变 AI 表现的。
"""

import torch
import torch.nn.functional as F

def demo_decoding():
    print("=" * 60)
    print("🎲 演示：大模型的抽卡玄学 (解码策略)")
    print("=" * 60)
    
    # 假设词表里只有 6 个词，这是模型最后一层输出的原始得分 (Logits)
    vocab = ["苹果", "香蕉", "手机", "电脑", "桌子", "宇宙"]
    logits = torch.tensor([5.0, 4.0, 2.0, 1.0, -1.0, -3.0])
    
    print(f"【原始词表】: {vocab}")
    print(f"【模型原始打分(Logits)】: {logits.numpy()}")
    
    # --------------------------------------------------
    # 1. 贪心搜索 (Greedy Search)
    # --------------------------------------------------
    print("\n【策略1：贪心搜索 (Greedy)】(对应 Temperature = 0)")
    greedy_idx = torch.argmax(logits).item()
    print(f"  无脑选择最高分的词: ➡️ '{vocab[greedy_idx]}'")
    print("  特点：绝对稳定，最适合做代码生成、数据提取、翻译。")

    # --------------------------------------------------
    # 2. Temperature (温度系数)
    # --------------------------------------------------
    print("\n【策略2：Temperature (温度)】")
    print("  公式：Softmax(Logits / Temperature)")
    
    t_normal = 1.0
    probs_normal = F.softmax(logits / t_normal, dim=-1)
    print(f"  - 正常温度 (T=1.0) 概率: {[f'{p:.2%}' for p in probs_normal]}")
    
    t_hot = 2.0
    probs_hot = F.softmax(logits / t_hot, dim=-1)
    print(f"  - 高温度 (T=2.0) 概率:   {[f'{p:.2%}' for p in probs_hot]}")
    print("    (高温让所有词概率变得平均，差词也有机会出场 → 适合写诗、头脑风暴)")
    
    t_cold = 0.5
    probs_cold = F.softmax(logits / t_cold, dim=-1)
    print(f"  - 低温度 (T=0.5) 概率:   {[f'{p:.2%}' for p in probs_cold]}")
    print("    (低温让强者更强，弱者接近0，倾向于保守 → 适合逻辑问答)")

    # --------------------------------------------------
    # 3. Top-K 采样
    # --------------------------------------------------
    print("\n【策略3：Top-K 采样】")
    K = 3
    print(f"  设定 K={K}，直接把得分排在第 {K} 名之后的词的概率强制变成 0。")
    print(f"  即使高温，也绝对不会选到'电脑'、'桌子'、'宇宙'这种离谱的词。")
    print("  特点：强行截断长尾，保证底线不翻车。")
    
    # --------------------------------------------------
    # 4. Top-P 采样 (核采样 Nucleus Sampling)
    # --------------------------------------------------
    print("\n【策略4：Top-P (核采样)】")
    print("  相比 Top-K 的死板切一刀，Top-P 是按概率从大到小累加。")
    print("  设定 P=0.9，只要累计概率达到 90% 就停止候选。")
    print("  特点：动态池子。如果第一个词概率极高(85%)，候选池就只有1-2个词；")
    print("  如果大家概率都很平均，候选池就会变得很大。这是目前生成式任务最推荐的策略。")

    print("\n💡 最佳实践指南：")
    print("  - 提取 JSON/写代码：Temp=0 (或极低)")
    print("  - 写日常文章/聊天：Temp=0.7, Top-P=0.95")
    print("  - 创意写作/写小说：Temp=1.2, Top-P=0.9, Top-K=50")

if __name__ == "__main__":
    demo_decoding()
