import asyncio
import websockets
import json

async def test():
    payload = {
        "message": "MCP 协议解决了什么痛点？",
        "mode": "fast",
        "history": []
    }
    
    async with websockets.connect("ws://localhost:8000/ws/chat") as ws:
        await ws.send(json.dumps(payload))
        while True:
            try:
                res = await ws.recv()
                print("Received:", res)
                data = json.loads(res)
                if data.get("type") == "stream_end" or "❌" in data.get("content", ""):
                    break
            except Exception as e:
                print("Error:", e)
                break

asyncio.run(test())
