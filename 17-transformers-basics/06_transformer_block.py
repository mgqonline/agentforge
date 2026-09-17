"""
第六课：完整 Transformer Encoder Block（组装核心零件）
=======================================================
前置知识：
  ✅ 第4课 - Attention 算子 (Q/K/V 矩阵运算)
  ✅ 第5课 - Positional Encoding (词序感知)

本课目标：
  把所有零件组装成一个完整的 Transformer Encoder Block，
  并理解每个零件的作用：
  
  输入 X
    │
    ▼
  [Multi-Head Self-Attention]   ← 上下文感知
    │
    + X (残差连接)               ← 防止梯度消失
    │
  [Layer Normalization]          ← 稳定训练
    │
    ▼
  [Feed-Forward Network (FFN)]  ← 特征变换与非线性
    │
    + (残差连接)
    │
  [Layer Normalization]
    │
    ▼
  输出（每个词都"理解"了整个句子的上下文）
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math


# ============================================================
# 零件一：Multi-Head Self-Attention（复用第4课）
# ============================================================

class MultiHeadSelfAttention(nn.Module):
    def __init__(self, d_model: int, num_heads: int, dropout: float = 0.1):
        super().__init__()
        assert d_model % num_heads == 0, "d_model 必须能被 num_heads 整除"
        
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads
        
        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x: torch.Tensor, mask: torch.Tensor = None):
        B, T, _ = x.shape
        
        # 生成 Q, K, V 并切分多头
        Q = self.q_proj(x).view(B, T, self.num_heads, self.d_k).transpose(1, 2)
        K = self.k_proj(x).view(B, T, self.num_heads, self.d_k).transpose(1, 2)
        V = self.v_proj(x).view(B, T, self.num_heads, self.d_k).transpose(1, 2)
        
        # Scaled Dot-Product Attention
        scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.d_k)
        
        # 可选 Mask（Decoder 中用于遮蔽未来 token）
        if mask is not None:
            scores = scores.masked_fill(mask == 0, float('-inf'))
        
        attn_weights = F.softmax(scores, dim=-1)
        attn_weights = self.dropout(attn_weights)
        
        context = torch.matmul(attn_weights, V)
        context = context.transpose(1, 2).contiguous().view(B, T, self.d_model)
        
        return self.out_proj(context), attn_weights


# ============================================================
# 零件二：Feed-Forward Network (FFN)
# 意义：Attention 负责"信息收集"（横向跨词），FFN 负责"特征变换"（纵向加深理解）
# 结构：Linear → GELU激活 → Dropout → Linear
# 参数：隐层通常是 d_model 的 4 倍（这是 BERT/GPT 的经验值）
# ============================================================

class FeedForwardNetwork(nn.Module):
    """
    两层全连接网络，对每个 token 的向量做非线性变换。
    
    比喻：Attention 是"开会讨论"（所有词互相交流），
          FFN 是"独自消化"（每个词独立处理刚才收到的信息）。
    """
    def __init__(self, d_model: int, d_ff: int = None, dropout: float = 0.1):
        super().__init__()
        d_ff = d_ff or d_model * 4  # 默认隐层是 d_model 的 4 倍
        
        self.net = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),          # 激活函数：比 ReLU 更平滑，现代大模型的标配
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout),
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# ============================================================
# 零件三：残差连接 + Layer Normalization
# 
# 残差连接（Residual Connection）：output = layer(x) + x
#   意义：直接开辟一条"高速公路"让梯度畅通无阻地反向传播，
#         彻底解决了深层网络的梯度消失问题。
#         （ResNet 发明的，被 Transformer 借鉴）
#
# Layer Normalization：对每个 token 的向量做归一化
#   意义：让每层的输入数值稳定在合理范围内，防止训练崩溃。
#         注意：和 Batch Norm 不同，LayerNorm 是对特征维度归一化，
#               不依赖 batch size，更适合序列模型。
# ============================================================


# ============================================================
# 完整 Transformer Encoder Block 组装
# ============================================================

class TransformerEncoderBlock(nn.Module):
    """
    一个完整的 Transformer Encoder 层。
    
    真实的 BERT-base 由 12 个这样的 Block 堆叠而成。
    GPT-3 由 96 个 Block 堆叠而成。
    Qwen2.5-72B 由 80 个 Block 堆叠而成（d_model=8192, num_heads=64）。
    """
    def __init__(self, d_model: int, num_heads: int, d_ff: int = None, dropout: float = 0.1):
        super().__init__()
        
        # 子层1: Multi-Head Self-Attention
        self.attention = MultiHeadSelfAttention(d_model, num_heads, dropout)
        self.norm1 = nn.LayerNorm(d_model)
        
        # 子层2: Feed-Forward Network
        self.ffn = FeedForwardNetwork(d_model, d_ff, dropout)
        self.norm2 = nn.LayerNorm(d_model)
        
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x: torch.Tensor, mask: torch.Tensor = None):
        # Sub-layer 1: Attention + 残差连接 + LayerNorm
        attn_out, attn_weights = self.attention(x, mask)
        x = self.norm1(x + self.dropout(attn_out))   # x + F(x)
        
        # Sub-layer 2: FFN + 残差连接 + LayerNorm
        ffn_out = self.ffn(x)
        x = self.norm2(x + self.dropout(ffn_out))     # x + G(x)
        
        return x, attn_weights


# ============================================================
# 完整的 Transformer Encoder（多层 Block 堆叠）
# ============================================================

class TransformerEncoder(nn.Module):
    """
    完整的 Transformer Encoder，由 N 个 Block 堆叠。
    这就是 BERT / RoBERTa 等理解类模型的核心架构。
    """
    def __init__(self, vocab_size: int, d_model: int, num_heads: int,
                 num_layers: int, max_seq_len: int = 512, dropout: float = 0.1):
        super().__init__()
        
        # 词嵌入层：把 token id 转成 d_model 维向量
        self.embedding = nn.Embedding(vocab_size, d_model)
        
        # 位置编码（简化版：用可学习的位置嵌入，BERT 的方案）
        self.pos_embedding = nn.Embedding(max_seq_len, d_model)
        
        # N 个 Encoder Block 堆叠
        self.blocks = nn.ModuleList([
            TransformerEncoderBlock(d_model, num_heads, dropout=dropout)
            for _ in range(num_layers)
        ])
        
        self.dropout = nn.Dropout(dropout)
        self.norm = nn.LayerNorm(d_model)  # 最终输出再 norm 一次
        self.d_model = d_model
    
    def forward(self, token_ids: torch.Tensor):
        B, T = token_ids.shape
        
        # 生成位置索引 [0, 1, 2, ..., T-1]
        positions = torch.arange(T, device=token_ids.device).unsqueeze(0)
        
        # 词嵌入 + 位置嵌入（直接相加）
        x = self.dropout(self.embedding(token_ids) + self.pos_embedding(positions))
        
        # 依次通过每个 Encoder Block
        all_attn_weights = []
        for block in self.blocks:
            x, attn_w = block(x)
            all_attn_weights.append(attn_w)
        
        return self.norm(x), all_attn_weights


# ============================================================
# 主程序：解剖一次完整的 Encoder 前向传播
# ============================================================

def main():
    print("=" * 60)
    print("第六课：完整 Transformer Encoder Block 解剖")
    print("=" * 60)
    
    # 模型参数（对标一个 tiny BERT）
    vocab_size = 1000    # 词表大小
    d_model = 64         # 每个 token 的向量维度
    num_heads = 4        # 注意力头数
    num_layers = 2       # Encoder Block 层数
    batch_size = 2       # 批量大小
    seq_len = 8          # 序列长度（8个 token）
    
    print(f"\n📐 模型配置:")
    print(f"  词表大小: {vocab_size}")
    print(f"  向量维度 d_model: {d_model}")
    print(f"  注意力头数: {num_heads}（每个头维度: {d_model // num_heads}）")
    print(f"  Encoder 层数: {num_layers}")
    print(f"  FFN 隐层维度: {d_model * 4}（= d_model × 4）")
    
    # 构建模型
    model = TransformerEncoder(
        vocab_size=vocab_size,
        d_model=d_model,
        num_heads=num_heads,
        num_layers=num_layers,
    )
    
    # 统计参数量
    total_params = sum(p.numel() for p in model.parameters())
    print(f"\n🔢 模型参数总量: {total_params:,} 个")
    print(f"  （真实 BERT-base: 110,000,000 个参数）")
    
    # 模拟输入：2个句子，每句8个token
    fake_token_ids = torch.randint(0, vocab_size, (batch_size, seq_len))
    print(f"\n📥 输入 Token IDs:")
    print(f"  shape: {fake_token_ids.shape}  (batch={batch_size}, seq_len={seq_len})")
    print(f"  内容: \n{fake_token_ids}")
    
    # 前向传播
    with torch.no_grad():
        output, all_attn_weights = model(fake_token_ids)
    
    print(f"\n📤 Encoder 输出:")
    print(f"  shape: {output.shape}  (batch={batch_size}, seq_len={seq_len}, d_model={d_model})")
    print(f"  ✅ 每个 token 的向量已经融合了整个句子的上下文语义！")
    
    print(f"\n🧠 各层 Attention 权重:")
    for i, attn_w in enumerate(all_attn_weights):
        print(f"  Block {i+1} Attention shape: {attn_w.shape}")
        print(f"    (batch={batch_size}, heads={num_heads}, seq={seq_len}, seq={seq_len})")
    
    # 可视化第一层第一个头的注意力矩阵
    print(f"\n👁️  第1层 第1个注意力头的权重矩阵（第1句话）:")
    print(f"  行=当前token，列=它关注其他token的权重（每行加起来=1）")
    head0_attn = all_attn_weights[0][0, 0].numpy().round(3)
    for row_idx, row in enumerate(head0_attn):
        bar = "".join(["█" * int(v * 20) for v in row])
        print(f"  tok[{row_idx}]: {bar}  {row}")
    
    print(f"\n{'='*60}")
    print(f"✨ 完整数据流总结:")
    print(f"  Token IDs {fake_token_ids.shape}")
    print(f"    ↓ Embedding + Positional Encoding")
    print(f"  词向量 [{batch_size}, {seq_len}, {d_model}]")
    print(f"    ↓ Block 1: Attention → 残差 → LayerNorm → FFN → 残差 → LayerNorm")
    print(f"    ↓ Block 2: 同上")
    print(f"  上下文感知向量 {output.shape}  ← 这就是 BERT 的输出！")
    print(f"\n  接下来只需在这个输出上接一个分类头，就能做情感分析、NER、问答等任务。")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
