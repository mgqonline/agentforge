import asyncio
import websockets
import json

async def test():
    payload = {
        "message": "MCP 协议解决了什么痛点？",
        "mode": "fast",
        "history": []
    }
    
    while True:
        try:
            async with websockets.connect("ws://localhost:8000/ws/chat") as ws:
                await ws.send(json.dumps(payload))
                while True:
                    try:
                        res = await ws.recv()
                        print("Received:", res)
                        data = json.loads(res)
                        if data.get("type") == "stream_end" or "❌" in data.get("content", ""):
                            return
                    except Exception as e:
                        print("Recv Error:", e)
                        return
        except Exception as e:
            print("Connect Error, retrying...", e)
            await asyncio.sleep(1)

asyncio.run(test())
