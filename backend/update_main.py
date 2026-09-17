import re

with open('main.py', 'r') as f:
    content = f.read()

new_ws = """
from worker import celery_app
from semantic_cache import semantic_cache
import redis.asyncio as aioredis
import json

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, session_id: str = "anonymous"):
    await manager.connect(websocket, session_id)
    redis_client = aioredis.from_url(redis_url)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"ws:{session_id}")
    
    async def listen_redis():
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                if data.get("type") == "task_complete":
                    # Cache the result if we have a pending query
                    if hasattr(websocket, 'pending_query') and hasattr(websocket, 'accumulated_response'):
                        semantic_cache.set_cache(websocket.pending_query, websocket.accumulated_response)
                    break
                
                # Accumulate stream chunks for caching
                if data.get("type") == "stream_chunk" and hasattr(websocket, 'accumulated_response'):
                    websocket.accumulated_response += data.get("content", "")
                
                try:
                    await websocket.send_json(data)
                except Exception as e:
                    print(f"WS send error: {e}")
                    break

    listen_task = None
    try:
        while True:
            data = await websocket.receive_json()
            user_msg = data.get("message", "")
            mode = data.get("mode", "fast")
            selected_model = data.get("model", model_name)
            image_data = data.get("image_data", None)
            history = data.get("history", [])

            if len(user_msg) > 4000:
                await websocket.send_json({"type": "stream_start"})
                await websocket.send_json({"type": "stream_chunk", "content": "\\n\\n> ⚠️ **[安全拦截]**: 您的输入文本过长。"})
                await websocket.send_json({"type": "stream_end"})
                continue
            
            if await check_sensitive_words(user_msg):
                await websocket.send_json({"type": "stream_start"})
                await websocket.send_json({"type": "stream_chunk", "content": "\\n\\n> 🛑 **[合规拦截]**: 您的提问包含敏感或违规词汇。"})
                await websocket.send_json({"type": "stream_end"})
                continue

            # 语义缓存检查 (Semantic Cache)
            cached_response = semantic_cache.get_cache(user_msg)
            if cached_response and mode == "fast":
                await websocket.send_json({"type": "status", "content": "⚡ 从语义缓存中极速返回..."})
                await websocket.send_json({"type": "stream_start"})
                await websocket.send_json({"type": "stream_chunk", "content": cached_response})
                await websocket.send_json({"type": "stream_end"})
                continue
            
            # 记录当前查询，以便任务完成时缓存
            websocket.pending_query = user_msg
            websocket.accumulated_response = ""

            # 发布任务到 Celery Worker
            celery_app.send_task(
                "worker.process_request",
                args=[session_id, user_msg, mode, selected_model, history, image_data]
            )

            # 启动 Redis 监听协程
            if listen_task is None or listen_task.done():
                listen_task = asyncio.create_task(listen_redis())

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        if listen_task:
            listen_task.cancel()
        await pubsub.unsubscribe(f"ws:{session_id}")
        await redis_client.aclose()
    except Exception as e:
        manager.disconnect(session_id)
        if listen_task:
            listen_task.cancel()
        print(f"Server Error in session {session_id}: {e}")
"""

# Replace from @app.websocket("/ws/chat") to the end (before if __name__ == "__main__":)
pattern = re.compile(r'@app\.websocket\("/ws/chat"\).*?(?=if __name__ == "__main__":)', re.DOTALL)
content = pattern.sub(new_ws + '\n', content)

with open('main.py', 'w') as f:
    f.write(content)
