import torch
import torch.nn as nn
import torch.nn.functional as F
import math

class BasicSelfAttention(nn.Module):
    """
    大模型底层 Attention 算子的核心手写实现
    基于论文 "Attention is All You Need"
    """
    def __init__(self, d_model, num_heads):
        super().__init__()
        self.d_model = d_model
        self.num_heads = num_heads
        
        # d_k 是每个注意力头的维度 (比如 512维 分给 8个头，每个头就是 64维)
        self.d_k = d_model // num_heads
        
        # 生成 Q, K, V 的线性层（这三个矩阵是大模型里最关键的参数权重）
        self.q_linear = nn.Linear(d_model, d_model)
        self.k_linear = nn.Linear(d_model, d_model)
        self.v_linear = nn.Linear(d_model, d_model)
        
        # 输出的线性映射
        self.out_proj = nn.Linear(d_model, d_model)
        
    def forward(self, x):
        batch_size, seq_len, _ = x.size()
        
        # 1. 矩阵相乘，生成 Q (Query), K (Key), V (Value)
        # 并把张量形状切割成多头: [batch, seq_len, d_model] -> [batch, num_heads, seq_len, d_k]
        q = self.q_linear(x).view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)
        k = self.k_linear(x).view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)
        v = self.v_linear(x).view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)
        
        # 2. 计算 Attention Score (注意力打分)
        # 公式: (Q 乘以 K的转置) 除以 根号d_k
        # 这一步算的是每一个词对其他所有词的“相关性”
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.d_k)
        
        # 3. Softmax 归一化
        # 把得分变成概率分布（每一行加起来等于 1，表示对各个词分配的注意力百分比）
        attn_weights = F.softmax(scores, dim=-1)
        
        # 4. 加权求和: 注意力权重 乘以 V
        # 根据刚才的百分比，把其他词的语义内容(V)按比例“吸”过来
        context = torch.matmul(attn_weights, v)
        
        # 5. 拼合多头，并做最后一次映射输出
        # [batch, num_heads, seq_len, d_k] -> [batch, seq_len, d_model]
        context = context.transpose(1, 2).contiguous().view(batch_size, seq_len, self.d_model)
        output = self.out_proj(context)
        
        return output, attn_weights

def main():
    print("=== 第四课：拆解大模型的心脏 —— Attention 算子 ===")
    
    # 模拟业务场景：有 1 句话，长度为 4 个 token，每个 token 被变成了 16 维向量
    # 例如这四个词是：["合", "同", "违", "约"]
    batch_size = 1
    seq_len = 4
    d_model = 16
    num_heads = 2
    
    # 伪造一个输入数据
    x = torch.randn(batch_size, seq_len, d_model)
    print(f"[输入形状]: {x.shape} -> (1句话, 4个词, 每个词16维)")
    
    # 实例化 Attention 算子并执行
    attention_layer = BasicSelfAttention(d_model=d_model, num_heads=num_heads)
    
    # 屏蔽随机梯度跟踪，只看计算结果
    with torch.no_grad():
        output, attn_weights = attention_layer(x)
    
    print(f"\n[输出形状]: {output.shape} -> (输出依然是1句话, 4个词, 每个词16维。但！每个词都吸收了上下文的语义！)")
    print(f"\n[注意力权重矩阵 (Attention Weights) 形状]: {attn_weights.shape}")
    print(" -> (batch=1, heads=2个头, seq_len=4, seq_len=4)")
    
    # 打印第一个头的 4x4 注意力打分矩阵
    print("\n[第一个注意力头 (Head 0) 的 4x4 关注度矩阵]:")
    print(attn_weights[0, 0].numpy().round(3))
    print("\n(每一行的数字加起来约等于1。比如第一行表示第1个词把自己的'注意力'按什么比例分配给了这4个词。)")

if __name__ == "__main__":
    main()
