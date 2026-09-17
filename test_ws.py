import asyncio
import websockets
import json
import base64

async def test():
    # create a dummy image (1x1 pixel png)
    img_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=="
    data_url = f"data:image/png;base64,{img_b64}"
    
    async with websockets.connect("ws://localhost:8000/ws/chat?session_id=test1&user_id=testuser") as ws:
        req = {
            "type": "chat",
            "message": "",
            "mode": "fast",
            "file_upload": {
                "name": "test.png",
                "type": "image/png",
                "data": data_url
            }
        }
        await ws.send(json.dumps(req))
        
        while True:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=5.0)
                msg = json.loads(resp)
                if msg.get("type") == "stream_chunk":
                    print("CHUNK:", repr(msg.get("content", "")))
                else:
                    print("MSG:", msg)
                if msg.get("type") == "stream_end":
                    break
            except asyncio.TimeoutError:
                print("TIMEOUT")
                break

asyncio.run(test())
