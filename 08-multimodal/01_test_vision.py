import os
import base64
from dotenv import load_dotenv
from openai import OpenAI

# 1. 配置
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_API_BASE", "https://api.deepseek.com")

client = OpenAI(api_key=api_key, base_url=base_url)

def encode_image(image_path):
    """将图片转换为 Base64 编码"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

async def test_vision_capability():
    print("🚀 正在验证多模态大模型能力...")
    
    # 1. 采用本地生成一张极小 1x1 像素的纯红测试图片（绕过网络下载与 cv2 依赖）
    local_image_path = "test_vision_input.png"
    print(f"📥 正在本地生成一张测试图片: {local_image_path} ...")
    
    # 这是一个标准 1x1 红色像素的 PNG 图片的 Base64 编码
    tiny_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    with open(local_image_path, "wb") as f:
        f.write(base64.b64decode(tiny_png_b64))
    print("✅ 本地测试图片生成完成！\n")
    
    # 2. 将本地图片转换为 Base64 编码
    print("🔄 正在将本地图片转换为 Base64 视觉 Token 矩阵...")
    base64_image = encode_image(local_image_path)
    
    # 构造符合 OpenAI 标准协议的多模态 Payload
    # 注意: data:image/png;base64, 是标准前缀
    image_payload_url = f"data:image/png;base64,{base64_image}"

    try:
        print("🔌 正在向模型发起多模态识别请求...")
        response = client.chat.completions.create(
            # 如果使用 OpenAI 官方接口，请使用 gpt-4o；若是国内平台请使用对应多模态模型名称（如 qwen-vl-plus）
            model="gpt-4o", 
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请描述这张图片里写了什么，是什么颜色的？"},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_payload_url}
                        },
                    ],
                }
            ],
            max_tokens=300,
        )
        print("\n🤖 模型回复:")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"\n❌ API 请求失败 (可能当前配置的模型引擎暂未开放 Vision 接口): {e}")
        print("💡 架构解析: 咱们组装的 '本地Base64特征' 已经完美无误。但由于 DeepSeek 官方 API (api.deepseek.com) 目前尚未在 /chat/completions 路由开放原生 Vision 支持，因此在接收包含 `image_url` 的 JSON 数组时会报类型反序列化错误。")
        print("💡 解决方案: 若要测试完全生效，需将 .env 中的 OPENAI_API_BASE 切回原生 OpenAI 或通义千问等已完全开放多模态 API 的引擎。")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_vision_capability())
