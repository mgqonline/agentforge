"""
第九课：稀疏架构 —— MoE (Mixture of Experts) 混合专家模型
============================================================
业务痛点：
  大模型能力要强，就必须增加参数量。
  但是，参数量增加（比如从 7B 增加到 100B），每次前向传播的计算量也会暴增，
  导致推理极慢、显存宽带被挤爆、推理成本企业无法承受。

MoE 的解法：
  在 Transformer 中，把庞大的 FFN (前馈神经网络) 拆分成 N 个小的"专家网络"（Experts）。
  增加一个"路由器（Router）"，每次只挑出最匹配当前 Token 的 2 个专家进行计算。
  
  例如 DeepSeek-V3 / Mixtral 8x7B：
  总参数虽然有几百亿/几千亿，但针对每个词，**只有一小部分参数被激活计算**。
  【效果】：用 7B 模型的推理速度和计算成本，跑出 70B 模型的能力！

本课目标：
  1. 理解 Router 是如何进行"路由分配"的
  2. 模拟 MoE 的稀疏激活过程
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

class SimpleMoELayer(nn.Module):
    """
    一个简化的混合专家 (MoE) 层
    替换传统的单一巨型 FFN
    """
    def __init__(self, d_model: int, num_experts: int = 8, top_k: int = 2):
        super().__init__()
        self.num_experts = num_experts
        self.top_k = top_k
        
        # 路由器网络 (Router)：负责判断把当前词分给哪个专家
        # 输入维度 d_model，输出维度 num_experts (对每个专家的打分)
        self.router = nn.Linear(d_model, num_experts, bias=False)
        
        # 8 个独立的"专家" (这里为了简化，用简单的 Linear 层代替 FFN)
        # 真实模型中，每个 Expert 都是一个完整的两层 FFN
        self.experts = nn.ModuleList([
            nn.Linear(d_model, d_model) for _ in range(num_experts)
        ])
        
    def forward(self, x: torch.Tensor):
        # x shape: [batch_size, seq_len, d_model]
        batch_size, seq_len, d_model = x.shape
        
        # 把 batch 和 seq_len 展平，方便对每个词独立路由
        # shape: [batch_size * seq_len, d_model]
        flat_x = x.view(-1, d_model)
        
        # 1. 路由器打分
        # router_logits: 每个词对 8 个专家的偏好得分
        router_logits = self.router(flat_x) 
        
        # 2. 选出得分最高的 Top-K (比如选 2 个) 专家
        # routing_weights: 选中的专家的权重百分比 (通过 softmax 算出)
        # selected_experts: 选中的专家的索引 (比如选了第 1 和 第 5 个专家)
        routing_weights, selected_experts = torch.topk(router_logits, self.top_k, dim=-1)
        routing_weights = F.softmax(routing_weights, dim=-1)
        
        # 3. 结果初始化
        final_output = torch.zeros_like(flat_x)
        
        # 【核心逻辑】：稀疏计算
        # 对每一个词，只让被选中的专家干活，其他专家"休息"
        for i in range(flat_x.size(0)):           # 遍历每个词
            for j in range(self.top_k):           # 遍历分配给它的 Top-K 个专家
                expert_idx = selected_experts[i, j].item()
                expert_weight = routing_weights[i, j]
                
                # 让指定的专家计算，并乘以它的权重，累加到输出中
                expert_out = self.experts[expert_idx](flat_x[i])
                final_output[i] += expert_weight * expert_out
                
        # 恢复形状
        return final_output.view(batch_size, seq_len, d_model), selected_experts

def demo_moe():
    print("=" * 60)
    print("🔀 演示：MoE (混合专家) 的路由过程")
    print("=" * 60)
    
    d_model = 16
    num_experts = 8
    top_k = 2
    
    moe_layer = SimpleMoELayer(d_model=d_model, num_experts=num_experts, top_k=top_k)
    
    # 模拟输入 4 个不同的词
    # 比如: ["苹果", "量子", "合同", "快乐"]
    words = torch.randn(1, 4, d_model)
    
    with torch.no_grad():
        output, selected_experts = moe_layer(words)
        
    print(f"总共有 {num_experts} 个专家在待命，每个词只选 {top_k} 个专家为其服务。\n")
    
    word_list = ["词0(可能偏科技)", "词1(可能偏文学)", "词2(可能偏法律)", "词3(可能偏日常)"]
    for i in range(4):
        experts = selected_experts[i].tolist()
        print(f"[{word_list[i]}] 被路由器分配给了 --> 专家 {experts[0]} 和 专家 {experts[1]}")
        
    print("\n💡 业务启示：")
    print("  1. 为什么 DeepSeek-V3 这么强还这么便宜？因为它用了极端的 MoE。")
    print("     数百亿参数放在显存里，但每次推理只有一小部分参数被加载进 GPU 计算核心。")
    print("  2. 在部署 MoE 模型时，它对【显存容量】要求极高（要装下所有专家），")
    print("     但对【计算算力(FLOPs)】的要求反而相对较低。")

if __name__ == "__main__":
    demo_moe()
