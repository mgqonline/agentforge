"""
第七课：LoRA 微调原理（低秩适配）
====================================
业务痛点：
  通用大模型在你的垂直业务（法律合同、医疗报告、客服话术）上表现一般。
  全量微调需要几十张 A100，花费几十万元，中小企业无法承受。

LoRA 的解法（Low-Rank Adaptation）：
  不修改原始模型的数百亿参数，只在关键位置"外挂"两个极小的矩阵 A 和 B。
  训练时只更新 A 和 B，冻结原始权重。
  参数量从 70B 降到仅需训练 ~200M，普通 4090 单卡即可搞定！

本课目标：
  1. 理解 LoRA 的数学原理（低秩分解）
  2. 手写 LoRA 层，看懂参数量的巨大差异
  3. 理解如何用 PEFT 库在真实模型上使用 LoRA（业务实战参考）
"""

import torch
import torch.nn as nn
import math


# ============================================================
# Part 1: LoRA 的数学原理
# ============================================================

def explain_lora_math():
    print("=" * 60)
    print("📐 LoRA 数学原理：低秩分解")
    print("=" * 60)
    print("""
原始 Transformer 中，Attention 的权重矩阵 W 的形状通常是 [d, d]。
例如 Qwen-7B 中，d=4096，那么一个 W 矩阵就有 4096×4096 = 16,777,216 个参数！

全量微调 (Full Fine-Tuning):
  更新所有参数  →  需要和预训练一样大的显存和计算量
  修改：W_new = W_original + ΔW
  ΔW 的参数量 = d × d = 16,777,216  （太大了！）

LoRA 的核心思想：
  ΔW 不需要是满秩矩阵！用两个低秩矩阵 A、B 来近似它：
  ΔW ≈ B × A
  
  其中：
    A 的形状：[r, d]   (r << d，r 通常只有 4、8、16、64)
    B 的形状：[d, r]
  
  参数量对比（d=4096, r=16）：
    全量微调 ΔW:   4096 × 4096 = 16,777,216 个参数
    LoRA A+B:      4096 × 16 + 16 × 4096 = 131,072 个参数
    压缩比: 16,777,216 / 131,072 = 128 倍！！！
  
  前向传播公式：
    y = W·x + (B·A)·x × (α/r)
         ↑原始路径      ↑LoRA旁路（训练时只更新这里）
    α 是缩放因子（超参数），通常设为 r 的倍数
""")


# ============================================================
# Part 2: 手写 LoRA 层
# ============================================================

class LoRALinear(nn.Module):
    """
    在一个普通的 Linear 层上叠加 LoRA 旁路。
    
    训练时：
      - original_weight 完全冻结（requires_grad=False）
      - lora_A 和 lora_B 参与梯度更新
    推理时：
      - 可以把 B@A 合并回 W（merge_weights），实现零推理开销
    """
    def __init__(
        self,
        in_features: int,
        out_features: int,
        r: int = 8,           # LoRA 秩（rank），越小参数越少，通常 4-64
        lora_alpha: int = 16, # 缩放因子
        dropout: float = 0.0,
    ):
        super().__init__()
        self.r = r
        self.lora_alpha = lora_alpha
        self.scaling = lora_alpha / r  # 最终的缩放系数
        
        # 原始 Linear 层（冻结）
        self.weight = nn.Parameter(torch.randn(out_features, in_features))
        self.bias = nn.Parameter(torch.zeros(out_features))
        
        # LoRA 旁路矩阵（只训练这两个！）
        self.lora_A = nn.Parameter(torch.randn(r, in_features))  # 下投影
        self.lora_B = nn.Parameter(torch.zeros(out_features, r)) # 上投影（初始化为0）
        
        self.lora_dropout = nn.Dropout(dropout)
        
        # 初始化：A 用高斯分布，B 初始化为 0（保证训练开始时 LoRA 不改变原始输出）
        nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))
        nn.init.zeros_(self.lora_B)
        
        # 冻结原始权重
        self.weight.requires_grad = False
        self.bias.requires_grad = False
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # 原始路径：W·x + bias（完全不更新）
        original_output = nn.functional.linear(x, self.weight, self.bias)
        
        # LoRA 旁路：(B·A)·x × scaling
        lora_output = (self.lora_dropout(x) @ self.lora_A.T @ self.lora_B.T) * self.scaling
        
        return original_output + lora_output
    
    def merge_weights(self):
        """
        推理优化：把 LoRA 矩阵合并回原始权重，消除推理时的额外计算开销。
        合并后的模型与原始模型结构完全一致，速度没有任何损失。
        """
        with torch.no_grad():
            self.weight.data += (self.lora_B @ self.lora_A) * self.scaling
            print("  ✅ LoRA 权重已合并回原始矩阵，推理无额外开销")


# ============================================================
# Part 3: 对比参数量
# ============================================================

def compare_params():
    print("\n" + "=" * 60)
    print("📊 参数量对比实验")
    print("=" * 60)
    
    d = 512  # 模拟 d_model 维度
    r = 8    # LoRA 秩
    
    # 普通 Linear 层
    normal_linear = nn.Linear(d, d)
    normal_params = sum(p.numel() for p in normal_linear.parameters())
    
    # LoRA Linear 层
    lora_linear = LoRALinear(d, d, r=r)
    total_params = sum(p.numel() for p in lora_linear.parameters())
    trainable_params = sum(p.numel() for p in lora_linear.parameters() if p.requires_grad)
    frozen_params = total_params - trainable_params
    
    print(f"\n[普通 Linear 层 ({d}→{d})]")
    print(f"  全量参数: {normal_params:,} 个")
    
    print(f"\n[LoRA Linear 层 ({d}→{d}, rank={r})]")
    print(f"  总参数: {total_params:,} 个")
    print(f"  🔒 冻结参数（原始权重，不训练）: {frozen_params:,} 个")
    print(f"  🔥 可训练参数（LoRA A+B）: {trainable_params:,} 个")
    print(f"  📉 参数压缩比: {normal_params / trainable_params:.1f}x ！！！")
    
    print(f"\n[推算真实业务场景：微调 7B 模型]")
    print(f"  全量微调所需可训练参数: ~7,000,000,000 个")
    print(f"  LoRA(r=16) 所需可训练参数: ~    40,000,000 个  (约 0.6%)")
    print(f"  显存需求从 ~140GB  →  ~16GB（单张 RTX 4090 可跑）")


# ============================================================
# Part 4: 验证 LoRA 的正确性
# ============================================================

def verify_lora():
    print("\n" + "=" * 60)
    print("🔬 验证 LoRA 前向传播")
    print("=" * 60)
    
    layer = LoRALinear(in_features=8, out_features=8, r=4)
    x = torch.randn(1, 4, 8)  # [batch=1, seq=4, d_model=8]
    
    with torch.no_grad():
        out_before = layer(x).clone()
        
        print(f"\n合并前输出 (前3个值): {out_before[0, 0, :3].numpy().round(4)}")
        
        # 合并 LoRA 权重到原始矩阵
        layer.merge_weights()
        
        out_after = layer(x)
        print(f"合并后输出 (前3个值): {out_after[0, 0, :3].numpy().round(4)}")
        
        diff = (out_before - out_after).abs().max().item()
        print(f"\n最大数值差异: {diff:.8f}  (约等于0，说明合并正确！)")


# ============================================================
# Part 5: 真实业务中如何用 PEFT 库使用 LoRA（代码参考）
# ============================================================

def show_peft_usage():
    print("\n" + "=" * 60)
    print("🚀 生产实战：用 PEFT 库对真实模型启用 LoRA")
    print("=" * 60)
    print("""
# ✅ 安装: pip install peft transformers
# 以下是生产级 LoRA 微调代码模板（需要有真实的训练数据）

from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model, TaskType

# 1. 加载基础模型（以 Qwen2.5-7B 为例）
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-7B-Instruct",
    torch_dtype=torch.float16,
    device_map="auto"
)

# 2. 定义 LoRA 配置
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,   # 任务类型：因果语言模型
    r=16,                            # LoRA 秩（越大能力越强，但参数越多）
    lora_alpha=32,                   # 缩放因子（通常是 r 的 2 倍）
    lora_dropout=0.05,
    # 关键：指定在哪些层注入 LoRA（Qwen 的 Attention 投影层）
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    bias="none",
)

# 3. 用 PEFT 包装模型（自动冻结原始权重，注入 LoRA 旁路）
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# 输出类似：trainable params: 40,370,176 || all params: 7,281,381,376 || trainable%: 0.5544

# 4. 准备数据集和训练（配合 trl 库的 SFTTrainer）
# ...（数据格式：{"instruction": "...", "output": "..."}）

# 5. 保存 LoRA 适配器（只保存几十MB，而不是几十GB的完整模型）
model.save_pretrained("./my_lora_adapter")
# 加载时：model = PeftModel.from_pretrained(base_model, "./my_lora_adapter")
""")


# ============================================================
# 主程序
# ============================================================

if __name__ == "__main__":
    explain_lora_math()
    compare_params()
    verify_lora()
    show_peft_usage()
    
    print("\n" + "=" * 60)
    print("✨ 小结：LoRA 的核心价值")
    print("-" * 60)
    print("  数学：用低秩矩阵 B×A 近似权重变化量 ΔW")
    print("  工程：参数量减少 100x+，单卡即可微调 7B 模型")
    print("  业务：让中小企业也能拥有专属垂直领域大模型")
    print("  适用：专有话术、领域知识增强、输出格式规范化")
    print()
    print("  ⚠️  注意：LoRA 不是万能的！")
    print("  如果问题是'模型根本不知道这个领域的知识'")
    print("  → 优先用 RAG（更快更灵活）")
    print("  如果问题是'模型知道但输出格式/风格不对'")
    print("  → 用 LoRA 微调（让模型记住你的风格）")
    print("=" * 60)
