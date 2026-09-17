import asyncio
import time
import websockets
from collections import Counter

CONCURRENCY = 800  # Number of concurrent connections to attempt
GATEWAY_URL = "ws://localhost:8080/ws/chat"
SUCCESS = 0
FAILED_RATE_LIMIT = 0
FAILED_OTHER = 0

async def connect_and_send(client_id):
    global SUCCESS, FAILED_RATE_LIMIT, FAILED_OTHER
    try:
        start = time.time()
        async with websockets.connect(GATEWAY_URL) as ws:
            # We just want to establish a connection to trigger rate limiting and proxy logic
            # Send a basic init message (the backend expects JSON)
            await ws.send('{"message": "Hello from stress test", "mode": "fast", "model": "deepseek-chat", "history": []}')
            
            # Read first response
            res = await ws.recv()
            latency = (time.time() - start) * 1000
            # print(f"[Client {client_id}] Success ({latency:.1f}ms): {res[:50]}...")
            SUCCESS += 1
    except websockets.exceptions.InvalidStatusCode as e:
        if e.status_code == 429:
            FAILED_RATE_LIMIT += 1
        else:
            FAILED_OTHER += 1
    except websockets.exceptions.ConnectionClosedError as e:
        if e.code == 1008:
            FAILED_RATE_LIMIT += 1
        else:
            print(f"WS Closed: {e}")
            FAILED_OTHER += 1
    except Exception as e:
        if FAILED_OTHER < 5:
            print(f"Error: {repr(e)}")
        FAILED_OTHER += 1

async def main():
    print(f"🚀 Starting Stress Test with {CONCURRENCY} concurrent WebSocket clients to {GATEWAY_URL}")
    start_time = time.time()
    
    tasks = [connect_and_send(i) for i in range(CONCURRENCY)]
    await asyncio.gather(*tasks)
    
    duration = time.time() - start_time
    print("-" * 40)
    print("📊 STRESS TEST RESULTS")
    print(f"⏱️ Total Time: {duration:.2f} seconds")
    print(f"✅ Successful Connections: {SUCCESS}")
    print(f"🛡️ Blocked by Rate Limiter (429/1008): {FAILED_RATE_LIMIT}")
    print(f"❌ Other Failures: {FAILED_OTHER}")
    print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())
