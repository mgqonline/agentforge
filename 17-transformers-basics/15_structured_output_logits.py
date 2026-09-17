"""
第十五课：100% 稳定的结构化输出 —— Logits 掩码 (Logits Masking)
=============================================================
业务痛点：
  在 Prompt 里让大模型“请严格输出 JSON 格式”，它大多数时候能听话，
  但偶尔还是会犯病，在 JSON 前面加上一句“好的，以下是您要的 JSON：\n```json”，
  导致下游业务代码直接 JSON.parse() 崩溃！

底层解法：Logits Masking (概率拦截)
  既然我们知道 JSON 必须以 '{' 开头，那在模型吐出第一个字的时候，
  我们直接把词表里除了 '{' 以外的另外 10万个词的概率，强行变成 -无限大 (-inf)。
  这样模型除了吐出 '{'，没有任何其他选择！这就是 `JSON Mode` 和 `Structured Output` 的底层原理。

本课目标：
  通过代码模拟，理解如何在最底层对大模型的输出“戴上镣铐”。
"""

import torch
import torch.nn.functional as F

def demo_structured_output():
    print("=" * 60)
    print("🔒 演示：结构化输出的底层魔法 (Logits Masking)")
    print("=" * 60)
    
    # 假设这是词表
    vocab = ["好的", "以下", "是", "{", "}", "\"name\"", "```json", "你好"]
    
    # 假设大模型正准备吐出回复的第 1 个字，这是它自己算出来的原始打分 (Logits)
    # 模型非常想说废话“好的”(10.0分)
    logits = torch.tensor([10.0, 5.0, 2.0, 4.0, 1.0, -1.0, 8.0, 6.0])
    
    print("【未干预时：模型想说废话】")
    probs = F.softmax(logits, dim=-1)
    best_word_idx = torch.argmax(probs).item()
    print(f"  各词概率: {[(vocab[i], f'{probs[i]:.1%}') for i in range(len(vocab))]}")
    print(f"  模型最终输出的第 1 个字是: ➡️ '{vocab[best_word_idx]}' (导致下游 JSON 解析崩溃！)\n")
    
    print("【启用结构化输出限制 (Logits Masking)】")
    print("  系统规则：规定当前输出必须是 JSON 的开头 '{' ")
    
    # 构建掩码：只允许 "{"（索引为3）通过，其他的全部变成负无穷
    mask = torch.full_like(logits, float('-inf'))
    mask[3] = 0.0  # 把 "{" 放行
    
    # 拦截开始！把模型的原始打分加上掩码
    masked_logits = logits + mask
    
    # 重新计算概率
    new_probs = F.softmax(masked_logits, dim=-1)
    new_best_word_idx = torch.argmax(new_probs).item()
    
    print(f"  被拦截后的 Logits: {masked_logits.numpy()}")
    print(f"  被拦截后的概率: {[(vocab[i], f'{new_probs[i]:.1%}') for i in range(len(vocab))]}")
    print(f"  模型被迫输出的第 1 个字是: ➡️ '{vocab[new_best_word_idx]}' (绝对完美的 JSON 开头！)\n")
    
    print("💡 业务启示：")
    print("  1. OpenAI 最新的 `Structured Outputs` 功能，底层就是用复杂的 FSM (有限状态机) ")
    print("     对每一次 Logits 生成做正则匹配和拦截，保证 100% 符合你规定的 Schema。")
    print("  2. 在开源界，非常有名的 `Outlines` 库就是专门做这件事的，")
    print("     它能让 Llama、Qwen 输出极其稳定的复杂 JSON 数据，是做 Agent 的必备利器！")

if __name__ == "__main__":
    demo_structured_output()
