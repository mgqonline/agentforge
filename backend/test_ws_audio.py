import asyncio
import websockets
import json
import base64
import os

async def test():
    # Read the dummy.wav we created earlier
    with open("dummy.wav", "rb") as f:
        audio_bytes = f.read()
    
    audio_b64 = "data:audio/wav;base64," + base64.b64encode(audio_bytes).decode('utf-8')
    
    payload = {
        "message": "请把这个语音转成文字",
        "mode": "expert",
        "model": "deepseek-chat",
        "audio_data": audio_b64,
        "file_upload": None,
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
