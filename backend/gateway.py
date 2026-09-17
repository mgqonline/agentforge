import os
import time
import json
import asyncio
import httpx
import websockets
import redis.asyncio as redis
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status, WebSocket
from fastapi.responses import JSONResponse, StreamingResponse

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")
DOWNSTREAM_URL = os.getenv("DOWNSTREAM_URL", "http://localhost:8000") # Forwarding to the main FastAPI app
MAX_CONNECTIONS = int(os.getenv("MAX_CONNECTIONS", 1000))
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", 600)) # e.g. 600 requests per IP per minute

# Global State
redis_client = None
http_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, http_client
    # Initialize Redis for rate limiting & token bucket
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    
    # High-concurrency connection pooling using HTTPX
    limits = httpx.Limits(max_keepalive_connections=MAX_CONNECTIONS, max_connections=MAX_CONNECTIONS)
    timeout = httpx.Timeout(60.0, connect=5.0)
    http_client = httpx.AsyncClient(limits=limits, timeout=timeout)
    
    print("🚀 [Gateway] Initialization complete (Redis + HTTP Connection Pool)")
    yield
    await http_client.aclose()
    await redis_client.aclose()
    print("🛑 [Gateway] Shutdown complete")

app = FastAPI(lifespan=lifespan, title="High-Concurrency API Gateway")

async def rate_limit(client_ip: str) -> bool:
    """Redis Sliding/Fixed Window Rate Limiting"""
    current_min = int(time.time() / 60)
    key = f"gateway:rate_limit:{client_ip}:{current_min}"
    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.incr(key)
        pipe.expire(key, 60)
        results = await pipe.execute()
    
    count = results[0]
    return count <= RATE_LIMIT_PER_MINUTE

@app.middleware("http")
async def gateway_middleware(request: Request, call_next):
    # Skip rate limiting for WebSockets as they're handled differently, or apply initial check
    if request.url.scheme in ("ws", "wss"):
        return await call_next(request)

    # 1. Rate Limiting Check
    client_ip = request.client.host if request.client else "127.0.0.1"
    is_allowed = await rate_limit(client_ip)
    if not is_allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"error": "Too Many Requests", "message": "Gateway Rate limit exceeded"}
        )
    
    # 2. Add Request Tracking ID
    request_id = os.urandom(8).hex()
    start_time = time.time()
    
    # 3. Process Request
    response = await call_next(request)
    
    # 4. Log Latency
    process_time = (time.time() - start_time) * 1000
    print(f"[{request_id}] {request.method} {request.url.path} - {response.status_code} - {process_time:.2f}ms")
    
    # 5. Inject tracking headers
    response.headers["X-Gateway-Request-ID"] = request_id
    response.headers["X-Gateway-Latency"] = f"{process_time:.2f}ms"
    return response

# Universal WebSocket Proxy Route
@app.websocket("/{path:path}")
async def websocket_proxy(websocket: WebSocket, path: str):
    await websocket.accept()
    
    # WS rate limiting based on connection attempt
    client_ip = websocket.client.host if websocket.client else "127.0.0.1"
    if not await rate_limit(client_ip):
        await websocket.close(code=1008, reason="Rate limit exceeded")
        return

    downstream_ws_url = f"{DOWNSTREAM_URL.replace('http', 'ws')}/{path}"
    
    try:
        # Use websockets lib to connect to downstream
        async with websockets.connect(downstream_ws_url) as downstream_ws:
            
            async def forward_client_to_server():
                try:
                    while True:
                        msg = await websocket.receive_text()
                        await downstream_ws.send(msg)
                except Exception:
                    pass
            
            async def forward_server_to_client():
                try:
                    async for msg in downstream_ws:
                        await websocket.send_text(msg)
                except Exception:
                    pass
            
            # Run both bidirectional streams concurrently
            await asyncio.gather(
                forward_client_to_server(),
                forward_server_to_client()
            )
    except Exception as e:
        print(f"⚠️ [Gateway WS Error]: {str(e)}")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass

# Universal HTTP Proxy Route
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def reverse_proxy(path: str, request: Request):
    await websocket.accept()
    
    # WS rate limiting based on connection attempt
    client_ip = websocket.client.host if websocket.client else "127.0.0.1"
    if not await rate_limit(client_ip):
        await websocket.close(code=1008, reason="Rate limit exceeded")
        return

    downstream_ws_url = f"{DOWNSTREAM_URL.replace('http', 'ws')}/{path}"
    
    try:
        # Use websockets lib to connect to downstream
        async with websockets.connect(downstream_ws_url) as downstream_ws:
            
            async def forward_client_to_server():
                try:
                    while True:
                        msg = await websocket.receive_text()
                        await downstream_ws.send(msg)
                except Exception:
                    pass
            
            async def forward_server_to_client():
                try:
                    async for msg in downstream_ws:
                        await websocket.send_text(msg)
                except Exception:
                    pass
            
            # Run both bidirectional streams concurrently
            await asyncio.gather(
                forward_client_to_server(),
                forward_server_to_client()
            )
    except Exception as e:
        print(f"⚠️ [Gateway WS Error]: {str(e)}")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
