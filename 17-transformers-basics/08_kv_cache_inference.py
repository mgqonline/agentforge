"""
第八课：大模型推理加速神器 —— KV Cache (键值缓存)
=================================================
业务痛点：
  大模型生成文本是"自回归"的（逐个字往外蹦）。
  生成第 100 个字时，模型需要看前 99 个字；
  生成第 101 个字时，模型需要看前 100 个字。
  如果每次都把前面的字重新算一遍 Attention，速度会慢到让人崩溃，且计算量呈平方级爆炸！

KV Cache 的解法：
  在生成过程中，把前面已经算过的历史词的 Key (K) 和 Value (V) 向量保存在显存里。
  下次生成新词时，历史词不用再算，直接从显存里读取出来，只计算当前这一个新词的 Q、K、V。
  这就是为什么大模型推理时，显存占用会随着对话越来越长而不断暴涨的原因！

本课目标：
  1. 直观感受"无 Cache" 和 "有 Cache" 在前向传播中的区别
  2. 理解为什么企业级大模型服务都在疯狂优化 KV Cache（如 PagedAttention）
"""

import torch
import torch.nn as nn
import time

def demo_autoregressive_generation():
    print("=" * 60)
    print("🚀 演示：为什么自回归生成需要 KV Cache")
    print("=" * 60)
    
    # 模拟参数
    seq_len = 5       # 已经生成的历史长度
    d_model = 64
    
    # 历史已经算好的 K 和 V（这就是放在显存里的 KV Cache）
    # 形状: [batch=1, seq_len=5, d_model=64]
    past_K = torch.randn(1, seq_len, d_model)
    past_V = torch.randn(1, seq_len, d_model)
    print(f"📁 显存中已保存的历史 KV Cache 形状: {past_K.shape} (保存了前 5 个词的信息)")
    
    # 现在要生成第 6 个词（当前最新输出的词）
    # 我们只对这**唯一的一个新词**计算 Q、K、V
    current_new_word_embed = torch.randn(1, 1, d_model) # [batch=1, seq=1, d_model=64]
    
    q_proj = nn.Linear(d_model, d_model)
    k_proj = nn.Linear(d_model, d_model)
    v_proj = nn.Linear(d_model, d_model)
    
    # 计算当前新词的 Q, K, V
    current_Q = q_proj(current_new_word_embed)
    current_K = k_proj(current_new_word_embed)
    current_V = v_proj(current_new_word_embed)
    
    print("\n【如果不使用 KV Cache】")
    print("你必须把前面的 5 个词重新输入模型，重新走一遍庞大的矩阵乘法！极度浪费算力！")
    
    print("\n【使用 KV Cache】")
    # 1. 拼接：把当前新词的 K, V 追加到历史的 KV Cache 后面
    # 新的 K 形状变成: [1, 5+1, 64] = [1, 6, 64]
    updated_K = torch.cat([past_K, current_K], dim=1)
    updated_V = torch.cat([past_V, current_V], dim=1)
    print(f"🔄 拼接后，最新的 K 矩阵形状: {updated_K.shape} (长度变成了 6)")
    
    # 2. 计算 Attention 
    # 注意：这里的 Q 只有 1 个词长，而 K 有 6 个词长！
    # 矩阵相乘: [1, 1, 64] @ [1, 64, 6] -> [1, 1, 6] (这个新词对前面 6 个词的注意力得分)
    scores = torch.matmul(current_Q, updated_K.transpose(-2, -1))
    print(f"🎯 Attention Score 形状: {scores.shape} (成功计算出新词对全文的注意力！)")
    
    # 乘以 V
    attn_weights = torch.softmax(scores, dim=-1)
    # [1, 1, 6] @ [1, 6, 64] -> [1, 1, 64]
    context = torch.matmul(attn_weights, updated_V)
    print(f"📤 最终输出向量形状: {context.shape} (直接可以用来预测第 7 个词了！)")
    
    print("\n💡 业务启示：")
    print("  1. 为什么用 vLLM 部署模型特别快？因为它引入了 PagedAttention，")
    print("     像操作系统管理内存一样，把这些庞大的 KV Cache 切成小块高效管理，")
    print("     极大提升了 GPU 显存的利用率和并发数。")
    print("  2. '上下文越长，显存占用越大'的元凶就是 KV Cache。")

if __name__ == "__main__":
    demo_autoregressive_generation()
