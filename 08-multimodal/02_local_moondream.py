import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from PIL import Image
import sys

# ==============================================================
# 02_local_moondream.py
# ==============================================================
# 本地测试多模态开源小模型 (Moondream2)
# Moondream2 是一个仅有 1.8B 参数的视觉语言模型 (VLM)，
# 极其适合在普通笔记本电脑上跑通多模态代码逻辑，无需昂贵的 GPU。
#
# 模型下载地址: https://huggingface.co/vikhyatk/moondream2
# ==============================================================

def main():
    # 使用我们刚刚下载到本地的模型绝对路径
    model_id = "/Users/mac/Documents/project/ailearning/models/moondream2"
    
    print(f"📥 正在从本地加载多模态模型: {model_id} ...")
    print("--------------------------------------------------")

    try:
        # 1. 加载模型与 Tokenizer
        model = AutoModelForCausalLM.from_pretrained(
            model_id, 
            trust_remote_code=True,
            torch_dtype=torch.float32
        )
        tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        
        # 将模型推入设备 (强制使用 CPU，因为 MPS 存在底层算子 bug 会导致输出 NaN 甚至崩溃)
        device = "cpu"
        model.to(device)
        model.eval()

        # 2. 读取要测试的图片
        image_path = "test_vision_input.jpeg" # 假设这是我们之前生成的那张图
        try:
            image = Image.open(image_path)
            print(f"✅ 成功读取测试图片: {image_path} (大小: {image.size})")
        except Exception as e:
            print(f"❌ 找不到图片 {image_path}，请准备一张测试图片。")
            sys.exit(1)

        # 3. 对图片进行视觉特征编码
        print("👁️ 模型正在'看'这张图片，提取视觉 Token...")
        enc_image = model.encode_image(image)

        # 4. 提出问题并推理
        prompt = "Describe this image in detail."
        print(f"👤 用户提问: {prompt}")
        print("🤖 模型思考中...\n")
        
        # 传入编码后的图片和文字问题，生成回答
        answer = model.answer_question(enc_image, prompt, tokenizer)
        
        print("========== 回答结果 ==========")
        print(answer)
        print("==============================")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ 模型加载或执行失败: {e}")
        print("⚠️ 常见原因排查:")
        print("  1. 缺少依赖: 请执行 `pip install transformers einops timm pillow`")
        print("  2. 网络阻断: 若看到 SSL 或 Connection Error，说明 HuggingFace 被墙或本地代理证书问题。建议手动去 HF 下载离线包并指定本地路径。")

if __name__ == "__main__":
    main()
