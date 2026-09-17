import unittest
import asyncio
import json
from fastapi.testclient import TestClient
from main import app, manager

class TestMainWebSocket(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Clear connections before tests
        manager.active_connections.clear()

    def test_connection_manager(self):
        # We can test manager logic directly
        # Since it uses async methods, we wrap in asyncio.run
        async def dummy_test():
            class DummyWS:
                async def accept(self): pass
                async def close(self, code, reason): pass
            
            ws1 = DummyWS()
            ws2 = DummyWS()
            
            await manager.connect(ws1, "session_1")
            self.assertIn("session_1", manager.active_connections)
            
            # Duplicated session handling
            await manager.connect(ws2, "session_1")
            self.assertEqual(manager.active_connections["session_1"], ws2)
            
            manager.disconnect("session_1")
            self.assertNotIn("session_1", manager.active_connections)
            
        asyncio.run(dummy_test())

    def test_websocket_chat_fast_mode(self):
        # We use FastAPI TestClient to test WebSocket
        with self.client.websocket_connect("/ws/chat?session_id=test_fast") as websocket:
            # Send initial fast mode request
            websocket.send_json({
                "message": "Hello",
                "mode": "fast",
                "history": []
            })
            
            # 1. First status (may receive task_started before status)
            data = websocket.receive_json()
            if data.get("type") == "task_started":
                data = websocket.receive_json()
            self.assertEqual(data.get("type"), "status")
            self.assertIn("检索企业知识库", data.get("content", ""))
            
            # Receive intermediate messages until stream_start
            while True:
                data = websocket.receive_json()
                if data["type"] == "stream_start":
                    break

            # Let it run and grab final result
            chunks = ""
            while True:
                try:
                    data = websocket.receive_json()
                    if data["type"] == "stream_chunk":
                        chunks += data["content"]
                    elif data["type"] == "stream_end":
                        break
                except Exception:
                    break

if __name__ == '__main__':
    unittest.main()
