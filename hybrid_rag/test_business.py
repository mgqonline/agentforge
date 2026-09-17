import requests
import json
import time

def test_sse():
    url = "http://127.0.0.1:8000/api/v1/chat/stream"
    payload = {"query": "什么是混合检索？"}
    
    print("🚀 开始闭环测试: 请求知识库问答 SSE 接口...")
    print("-" * 50)
    print(f"👤 用户提问: {payload['query']}")
    print("🤖 助手流式回复:")
    
    try:
        # 发起流式 POST 请求
        with requests.post(url, json=payload, stream=True, timeout=60) as response:
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        data_str = decoded_line[6:]
                        if data_str == "[DONE]":
                            print("\n" + "-" * 50)
                            print("✅ 业务闭环测试完成：流式输出结束 [DONE]")
                            break
                        try:
                            data = json.loads(data_str)
                            # 模拟打字机效果输出
                            print(data.get("content", ""), end="", flush=True)
                        except json.JSONDecodeError:
                            pass
    except Exception as e:
        print(f"\n❌ 业务测试请求失败: {e}")

if __name__ == "__main__":
    # 等待服务端启动完毕
    time.sleep(2)
    test_sse()
