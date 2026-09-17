"""
第十一课：打破内存墙 —— FlashAttention 原理
===================================================
业务痛点：
  传统的 Attention 计算需要实例化一个巨大的 N×N 注意力打分矩阵（N 是序列长度）。
  当处理 100K 上下文时，单单这个矩阵就会吃掉数百 GB 显存，并且 GPU 在显存（HBM）
  和计算核心（SRAM）之间搬运这个矩阵的时间，远远超过了实际计算的时间！
  这被称为“内存墙（Memory Wall）”。

FlashAttention 的解法：
  1. 分块计算 (Tiling)：把庞大的 Q、K、V 切成小块，放入速度极快的 SRAM 中直接算到底，
     坚决不在慢速的显存(HBM)中保存那个巨大的 N×N 中间矩阵。
  2. 重计算 (Recomputation)：在反向传播时，不读取缓存的 N×N 矩阵，而是重新算一遍。
     听起来反直觉（算两次），但因为计算比读写显存快得多，整体速度反而飙升 3 倍！

本课目标：
  通过模拟对比，理解为什么计算密集和访存密集的区别。
"""

import time

def demo_memory_wall():
    print("=" * 60)
    print("⚡ 演示：理解 GPU 的『内存墙』问题")
    print("=" * 60)
    
    print("【背景知识】")
    print("GPU 的计算核心 (SRAM) 极快，但容量极小（只有几十 MB）。")
    print("GPU 的显存 (HBM) 巨大（如 80GB），但读写速度比 SRAM 慢得多。")
    
    print("\n【传统 Attention 的糟糕做法】")
    print("1. Q 乘 K 算出 N×N 的巨大矩阵，写回慢速显存 HBM。")
    print("2. 从 HBM 读出这个巨型矩阵，算 Softmax，再写回 HBM。")
    print("3. 从 HBM 读出 Softmax 结果，乘 V，再写回 HBM。")
    print("结论：GPU 核心一直在发呆，等待数据从 HBM 慢吞吞地运过来。")
    
    print("\n【FlashAttention 的破局思路 (分块 Tiling)】")
    print("1. 把 Q,K,V 切成小块（恰好能塞进极快的 SRAM）。")
    print("2. 在 SRAM 里，一气呵成完成 Q×K、Softmax、乘V。")
    print("3. 把最终的一小块结果写回 HBM。")
    print("结论：彻底消灭了那个中间的 N×N 庞大矩阵，速度飙升 3-4 倍！")
    
    print("\n💡 业务启示：")
    print("  在部署大模型时（如使用 vLLM 或 TGI），通常都会看到一行启动日志：")
    print("  'FlashAttention-2 activated.'")
    print("  正是这项技术，让支持 128K 甚至 1M 长文本大模型的商用变成了现实。")

if __name__ == "__main__":
    demo_memory_wall()
