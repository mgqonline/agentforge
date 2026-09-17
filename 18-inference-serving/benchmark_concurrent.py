import asyncio
import aiohttp
import time
import json
import argparse
from typing import List, Dict

async def fetch(session: aiohttp.ClientSession, url: str, payload: dict, headers: dict, request_id: int) -> Dict:
    """发送单个异步推理请求"""
    start_time = time.time()
    try:
        async with session.post(url, json=payload, headers=headers) as response:
            response_data = await response.json()
            latency = time.time() - start_time
            return {
                "id": request_id,
                "status": response.status,
                "latency": latency,
                "response": response_data
            }
    except Exception as e:
        latency = time.time() - start_time
        return {
            "id": request_id,
            "status": 500,
            "latency": latency,
            "error": str(e)
        }

async def benchmark(api_url: str, concurrency: int, total_requests: int, prompt: str, model: str):
    """压测主逻辑"""
    print(f"🚀 开始压测，并发数: {concurrency}, 总请求: {total_requests}, 模型: {model}")
    
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model, 
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 100
    }

    start_time = time.time()
    results = []

    # 使用 Semaphore 控制最大并发
    semaphore = asyncio.Semaphore(concurrency)

    async def sem_fetch(session, req_id):
        async with semaphore:
            return await fetch(session, api_url, payload, headers, req_id)

    async with aiohttp.ClientSession() as session:
        tasks = [sem_fetch(session, i) for i in range(total_requests)]
        # 等待所有请求完成
        results = await asyncio.gather(*tasks)

    total_time = time.time() - start_time
    
    # 统计结果
    successful_requests = [r for r in results if r["status"] == 200]
    failed_requests = len(results) - len(successful_requests)
    
    if successful_requests:
        avg_latency = sum(r["latency"] for r in successful_requests) / len(successful_requests)
        max_latency = max(r["latency"] for r in successful_requests)
        min_latency = min(r["latency"] for r in successful_requests)
    else:
        avg_latency = max_latency = min_latency = 0

    throughput = len(successful_requests) / total_time if total_time > 0 else 0

    print("\n" + "="*40)
    print("📊 压测结果报告")
    print("="*40)
    print(f"总耗时: {total_time:.2f} 秒")
    print(f"成功请求: {len(successful_requests)}")
    print(f"失败请求: {failed_requests}")
    print(f"吞吐量 (QPS): {throughput:.2f} req/s")
    if successful_requests:
        print(f"平均延迟: {avg_latency:.4f} 秒")
        print(f"最小延迟: {min_latency:.4f} 秒")
        print(f"最大延迟: {max_latency:.4f} 秒")
    print("="*40)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="大模型推理服务高并发压测工具")
    parser.add_argument("--url", type=str, default="http://localhost:8000/v1/chat/completions", help="API 接口地址")
    parser.add_argument("-m", "--model", type=str, default="Qwen/Qwen2.5-0.5B-Instruct", help="请求的模型名称")
    parser.add_argument("-c", "--concurrency", type=int, default=10, help="并发数量")
    parser.add_argument("-n", "--requests", type=int, default=50, help="总请求数")
    parser.add_argument("-p", "--prompt", type=str, default="请详细解释一下什么是连续批处理(Continuous Batching)？", help="测试 Prompt")
    
    args = parser.parse_args()
    
    # 运行异步压测
    asyncio.run(benchmark(args.url, args.concurrency, args.requests, args.prompt, args.model))
