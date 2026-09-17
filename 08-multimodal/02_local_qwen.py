import os
import torch
import sys
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

# ==============================================================
# 02_local_qwen.py
# ==============================================================
# 本地测试多模态开源模型 (Qwen2.5-VL-7B-Instruct)
# ==============================================================

def main():
    model_id = "/Users/mac/Documents/project/ailearning/models/Qwen2.5-VL-7B-Instruct"
    
    if not os.path.exists(model_id):
        print(f"❌ 模型目录 {model_id} 不存在。请先运行 download_ms.py 等待下载完成。")
        sys.exit(1)
        
    print(f"📥 正在从本地加载多模态模型: {model_id} ...")
    print("--------------------------------------------------")

    try:
        # 1. 加载模型与 Processor
        # 注意：这里为了在无独立显卡的电脑上运行，使用 CPU。如果内存不够，可以尝试 torch_dtype=torch.bfloat16 (如果CPU支持) 或降低精度。
        # 如果有 GPU / Apple Silicon，可尝试将 device_map 设置为 "auto" 或设备名
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_id, 
            torch_dtype=torch.float32,
            device_map="cpu"
        )
        processor = AutoProcessor.from_pretrained(model_id)
        
        # 2. 准备问题与图片
        image_path = "test_vision_input.jpeg" 
        if not os.path.exists(image_path):
            print(f"❌ 找不到图片 {image_path}，请准备一张测试图片。")
            sys.exit(1)
            
        print(f"✅ 成功读取测试图片: {image_path}")

        # 3. 构造请求
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image_path},
                    {"type": "text", "text": "Describe this image in detail."},
                ],
            }
        ]

        # 4. 使用 Processor 进行预处理
        print("👁️ 模型正在'看'这张图片...")
        text = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to("cpu")

        # 5. 推理生成
        print("👤 用户提问: Describe this image in detail.")
        print("🤖 模型思考中...\n")
        
        generated_ids = model.generate(**inputs, max_new_tokens=256)
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        
        answer = processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]
        
        print("========== 回答结果 ==========")
        print(answer)
        print("==============================")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ 模型加载或执行失败: {e}")
        print("⚠️ 确保安装了对应依赖: `pip install qwen-vl-utils transformers torchvision accelerate`")

if __name__ == "__main__":
    main()
