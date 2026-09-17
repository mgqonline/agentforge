#!/bin/bash
set -e

# 1. 生成自定义测试数据集
python 19-model-finetuning/generate_dataset.py

# 获取之前下载到本地的模型绝对路径
MODEL_PATH="/Users/mac/.cache/modelscope/models/qwen--Qwen2.5-0.5B-Instruct/snapshots/master"

echo "=========================================="
echo "🚀 开始在 Mac M芯片 上使用 MLX 进行 LoRA 微调"
echo "使用模型：$MODEL_PATH"
echo "=========================================="

# 2. 运行 mlx-lm 微调命令
# 参数说明：
# --data 19-model-finetuning/data : 指定数据集目录（里面包含 train.jsonl 和 valid.jsonl）
# --iters 100 : 训练步数（这里为了快速演示设为 100 步）
# --batch-size 2 : 批次大小，Mac 显存足够的话可以调大
# --num-layers 4 : 参与微调的层数，通常为了节省显存和加快速度，只微调最后几层
mlx_lm.lora \
    --model "$MODEL_PATH" \
    --train \
    --data 19-model-finetuning/data \
    --iters 100 \
    --batch-size 2 \
    --num-layers 4 \
    --learning-rate 1e-4

echo "=========================================="
echo "✅ 微调完成！生成的适配器权重 (Adapters) 保存在了当前目录的 adapters/ 下。"
echo "测试微调效果可执行："
echo "mlx_lm.generate --model $MODEL_PATH --adapter-path adapters --prompt \"<|im_start|>user\n你们公司的核心价值观是什么？<|im_end|>\n<|im_start|>assistant\n\" --max-tokens 50"
echo "=========================================="
