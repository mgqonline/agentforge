import asyncio
import websockets
import json
import base64

async def test():
    with open("test.mp3", "rb") as f:
        mp3_bytes = f.read()
    
    encoded = base64.b64encode(mp3_bytes).decode('utf-8')
    data_uri = f"data:audio/mpeg;base64,{encoded}"
    
    payload = {
        "message": "",
        "mode": "expert",
        "file_upload": {
            "name": "test.mp3",
            "type": "audio/mpeg",
            "data": data_uri
        },
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
