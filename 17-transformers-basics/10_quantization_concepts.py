"""
第十课：大模型瘦身术 —— 模型量化 (Quantization)
===================================================
业务痛点：
  一个 72B（720亿参数）的大模型，如果用标准的 16位浮点数（FP16）存储，
  需要的显存 = 72,000,000,000 × 2 Bytes ≈ 144 GB。
  这意味着你需要 2 台 8卡 A10（或者 2张 80G A100）才能勉强把它跑起来，极其昂贵！

量化的解法：
  把 16位浮点数（FP16），强制压缩成 8位整数（INT8），甚至是 4位整数（INT4）。
  【效果】：显存占用直接缩小 2 倍甚至 4 倍！用一张 24G 显存的 4090，就能跑起 32B 的大模型。

本课目标：
  1. 直观感受量化是如何把高精度小数变成低精度整数的
  2. 理解量化过程中的"精度损失"（为什么量化模型有时会变笨）
"""

import torch

def demo_quantization():
    print("=" * 60)
    print("🗜️ 演示：模型量化 (FP16 -> INT8) 的数学原理")
    print("=" * 60)
    
    # 1. 模拟大模型中的一层权重（原本是非常高精度的小数）
    # 假设这是原始的 FP16 权重矩阵
    original_weights = torch.tensor([
        [0.1234, -0.9876, 1.4567],
        [-0.5555, 0.0001, 2.3456]
    ])
    
    print("【原始权重 (FP16)】高精度，非常占空间:")
    print(original_weights)
    print(f"数据类型: {original_weights.dtype}\n")
    
    # 2. 计算缩放因子 (Scale)
    # 我们要把它压缩到 INT8（范围是 -127 到 127）
    # 找出原矩阵绝对值的最大值 (max_abs)
    max_val = original_weights.abs().max() 
    # 把最大值映射到 127
    scale = 127.0 / max_val  
    
    print(f"最大绝对值: {max_val:.4f}, 计算出的缩放因子 (Scale): {scale:.4f}\n")
    
    # 3. 执行量化 (Quantize)
    # 将原权重乘以缩放因子，然后四舍五入变成整数！
    quantized_weights = torch.round(original_weights * scale).to(torch.int8)
    
    print("【量化后的权重 (INT8)】低精度，空间缩小一半！")
    print(quantized_weights)
    print(f"数据类型: {quantized_weights.dtype}\n")
    
    # 4. 反量化 (Dequantize) - 推理时恢复成小数进行计算
    # 将整数除以刚才的缩放因子
    dequantized_weights = (quantized_weights.float() / scale)
    
    print("【反量化恢复的权重 (FP32)】推理时使用")
    print(dequantized_weights)
    
    # 5. 计算精度损失
    # 比较原始权重和反量化后的权重
    diff = (original_weights - dequantized_weights).abs()
    print("\n【精度损失 (Error)】")
    print(diff)
    print(f"最大误差: {diff.max().item():.6f}")
    
    print("\n💡 业务启示：")
    print("  1. 常见的量化格式：GGUF, AWQ, GPTQ。你在网上下载大模型时，看到带有 '-AWQ' 或 '-Q4_K_M' 尾缀的模型，就是量化过的。")
    print("  2. INT4 量化能把模型压缩到原来的 1/4，但会导致较明显的数学能力和逻辑推理能力下降。")
    print("  3. 生产部署建议：在显存允许的情况下，优先使用 INT8（几乎无损）；极度缺显存才用 INT4。")

if __name__ == "__main__":
    demo_quantization()
