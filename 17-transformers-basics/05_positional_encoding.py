"""
第五课：位置编码（Positional Encoding）
=========================================
核心问题：Attention 机制是"无序"的——它同时看所有词，但不知道词的先后顺序。
业务影响：如果没有位置编码，"我欠你100元" 和 "你欠我100元" 对大模型来说没有任何区别！

本课目标：
  1. 理解正弦位置编码（Sinusoidal PE）的设计原理
  2. 可视化位置编码矩阵，直观感受"位置信息"是如何被注入的
  3. 理解现代大模型（Qwen/Llama）用的 RoPE 旋转位置编码的改进思路
"""

import torch
import math


# ============================================================
# Part 1: 经典正弦位置编码（Transformer 原论文方案）
# ============================================================

class SinusoidalPositionalEncoding(torch.nn.Module):
    """
    原始论文 "Attention Is All You Need" 中提出的位置编码方案。
    
    核心思路：
      - 用一系列不同频率的正弦/余弦波，为序列中每个位置生成一个唯一的"指纹"
      - 偶数维度用 sin，奇数维度用 cos
      - 公式：PE(pos, 2i)   = sin(pos / 10000^(2i/d_model))
              PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
    """
    
    def __init__(self, d_model: int, max_seq_len: int = 512):
        super().__init__()
        
        # 构建位置编码矩阵 shape: [max_seq_len, d_model]
        pe = torch.zeros(max_seq_len, d_model)
        
        # positions: [0, 1, 2, ..., max_seq_len-1] 每个词的位置索引
        positions = torch.arange(0, max_seq_len).unsqueeze(1).float()
        
        # div_term: 频率的分母，控制每一维用什么"频率"的波
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )
        
        # 偶数维度填 sin，奇数维度填 cos
        pe[:, 0::2] = torch.sin(positions * div_term)  # 第 0, 2, 4, ... 列
        pe[:, 1::2] = torch.cos(positions * div_term)  # 第 1, 3, 5, ... 列
        
        # 注册为 buffer（不参与梯度更新，但会随模型保存）
        self.register_buffer('pe', pe.unsqueeze(0))  # [1, max_seq_len, d_model]
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: [batch_size, seq_len, d_model] - 词嵌入向量
        返回：词嵌入 + 位置编码（两者直接相加）
        """
        seq_len = x.size(1)
        return x + self.pe[:, :seq_len, :]


# ============================================================
# Part 2: 可视化位置编码（最直观理解）
# ============================================================

def visualize_positional_encoding(seq_len=20, d_model=16):
    """打印位置编码矩阵，直观感受不同位置的"指纹"差异"""
    
    pe_layer = SinusoidalPositionalEncoding(d_model=d_model, max_seq_len=seq_len)
    # 取出 pe 矩阵 shape: [seq_len, d_model]
    pe_matrix = pe_layer.pe.squeeze(0)[:seq_len, :]
    
    print(f"位置编码矩阵 (前 {seq_len} 个位置，每个位置 {d_model} 维):")
    print(f"{'位置':>4}", end="")
    for i in range(d_model):
        print(f"  dim{i:02d}", end="")
    print()
    print("-" * (6 + d_model * 7))
    
    for pos in range(seq_len):
        print(f"{pos:>4}", end="")
        for val in pe_matrix[pos]:
            print(f"  {val.item():+.2f}", end="")
        print()
    
    print(f"\n💡 观察规律:")
    print(f"  1. 每一行（位置）都是唯一的，就像每个词的'地址指纹'")
    print(f"  2. 左边几列变化快（高频），右边几列变化慢（低频）")
    print(f"  3. 位置 {seq_len//2} 和位置 {seq_len//2+1} 的向量很相似（相邻位置有连续性）")


# ============================================================
# Part 3: 现代大模型用的 RoPE（旋转位置编码）简介
# ============================================================

def explain_rope():
    """
    RoPE (Rotary Position Embedding) 是 Llama / Qwen / DeepSeek 等大模型都在用的现代方案。
    
    和原始 PE 的区别：
      - 原始 PE：直接把位置编码"加"到词向量上（位置和内容混在一起）
      - RoPE：把位置信息编码成一个"旋转角度"，在计算 Attention Score 时
               旋转 Q 和 K 向量，而不是改变原始词向量本身
               
    业务优势：
      - 天然支持超长上下文（外推能力强），这就是为什么 Qwen2.5 能支持 128K context
      - 相对位置感知更好：词距越近，旋转角度差越小，Attention Score 就越高
    """
    print("\n" + "="*55)
    print("📐 RoPE 旋转位置编码（现代大模型标配）")
    print("="*55)
    print("""
原始 PE（正弦方案）:
  词向量  +  位置向量  →  送入 Attention
  [苹果]  + [pos=3]   →  混合向量

RoPE（旋转方案）:
  词向量  经过旋转矩阵（旋转角度由位置决定）  →  再做 Attention
  [苹果]  × R(θ × 3)  →  带位置感知的向量

关键洞察：
  Q_rotated · K_rotated 的结果，自然包含了相对位置差 (m-n)
  这让模型天然学会"两个词相距多远"，而不只是"在第几个位置"
  
  上下文窗口对比：
    原始正弦 PE  →  BERT: 512 tokens
    RoPE         →  Qwen2.5: 128K tokens（扩展后甚至 1M tokens）
""")


# ============================================================
# Part 4: 实战演示 - 位置编码如何影响语义
# ============================================================

def demo_position_matters():
    """
    业务案例：演示位置编码让模型能区分词序不同的句子
    "我欠你100元" vs "你欠我100元" - 词相同但顺序不同，含义完全相反
    """
    print("\n" + "="*55)
    print("🔍 业务演示：位置编码如何区分语序")
    print("="*55)
    
    d_model = 8
    pe_layer = SinusoidalPositionalEncoding(d_model=d_model, max_seq_len=10)
    
    # 假设词表只有4个词的 embedding（随机初始化，代表词义）
    # 我=0, 欠=1, 你=2, 100元=3
    word_embeddings = torch.randn(4, d_model)
    
    # 句子1: "我(0) 欠(1) 你(2) 100元(3)"  → 位置 0,1,2,3
    sentence1_ids = [0, 1, 2, 3]
    sentence1_embed = word_embeddings[sentence1_ids].unsqueeze(0)
    sentence1_with_pe = pe_layer(sentence1_embed).squeeze(0)
    
    # 句子2: "你(2) 欠(1) 我(0) 100元(3)"  → 位置 0,1,2,3 (同样的位置！)
    sentence2_ids = [2, 1, 0, 3]
    sentence2_embed = word_embeddings[sentence2_ids].unsqueeze(0)
    sentence2_with_pe = pe_layer(sentence2_embed).squeeze(0)
    
    # 计算两句话第一个词的向量差异
    diff = (sentence1_with_pe[0] - sentence2_with_pe[0]).norm().item()
    
    print(f"\n句子1: 我(位置0) 欠(位置1) 你(位置2) 100元(位置3)")
    print(f"句子2: 你(位置0) 欠(位置1) 我(位置2) 100元(位置3)\n")
    print(f"句子1 '我' 在位置0 的最终向量: {sentence1_with_pe[0].detach().numpy().round(2)}")
    print(f"句子2 '你' 在位置0 的最终向量: {sentence2_with_pe[0].detach().numpy().round(2)}")
    print(f"\n向量差异 (L2 距离): {diff:.4f}")
    print(f"\n✅ 结论：即使是相同的词，在不同的位置上，其最终向量完全不同！")
    print(f"   这使得模型能区分 '我欠你' 和 '你欠我' 这两个截然相反的含义。")


# ============================================================
# 主程序
# ============================================================

if __name__ == "__main__":
    print("=" * 55)
    print("第五课：位置编码（Positional Encoding）")
    print("=" * 55)
    
    print("\n【Part 1】位置编码矩阵可视化")
    print("-" * 55)
    visualize_positional_encoding(seq_len=8, d_model=8)
    
    explain_rope()
    demo_position_matters()
    
    print("\n" + "="*55)
    print("✨ 小结：")
    print("  - 位置编码解决了 Attention '无序' 的天生缺陷")
    print("  - 原始正弦方案：简单直接，BERT/GPT-2 在用")
    print("  - RoPE：现代大模型标配，支持超长上下文")
    print("  - 下一课：把 Attention + 位置编码 + FFN 组装成完整的 Transformer Block")
    print("="*55)
