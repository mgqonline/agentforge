import asyncio
import websockets
import json

async def test():
    async with websockets.connect('ws://localhost:8000/ws/chat?session_id=test_session') as websocket:
        await websocket.send(json.dumps({
            "message": "",
            "mode": "fast",
            "image_data": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAgAAZABkAAD",
            "history": []
        }))
        while True:
            response = await websocket.recv()
            print(response)
            data = json.loads(response)
            if data['type'] == 'stream_end':
                break

asyncio.run(test())
