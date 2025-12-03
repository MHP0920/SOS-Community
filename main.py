"""
Copyright (c) 2025 Nexuron
Licensed under the Nexuron Custom License — see LICENSE.
"""
from fastapi import FastAPI, HTTPException, Request, status, Query, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
import httpx
import json
import os
import time
import asyncio
from database import redis_client
from models import RequestId, PageNumber, PageLimit, SafeString
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

app = FastAPI()

# --- Configuration ---
REGISTRY_URL = os.getenv("REGISTRY_URL", "http://127.0.0.1:8001")
MY_URL = os.getenv("MY_URL", "http://localhost:8003")

# Global HTTP Client
http_client: Optional[httpx.AsyncClient] = None

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "https://sos.info.vn", "https://www.sos.info.vn"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def paginate_data(items: list, page: int, limit: int) -> Dict[str, Any]:
    total = len(items)
    start = (page - 1) * limit
    end = start + limit
    return {
        "data": items[start:end],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit
    }

async def forward_request(method: str, path: str, json_data: Optional[dict] = None, headers: Optional[dict] = None, raw: bool = False):
    client = http_client
    try:
        if method == "GET":
            resp = await client.get(f"{REGISTRY_URL}{path}", headers=headers)
        else:
            raise HTTPException(status_code=405, detail="Method not allowed")
        
        if resp.status_code >= 400:
            try:
                error_detail = resp.json().get("detail", "Error from upstream server")
            except Exception:
                error_detail = resp.text or "Error from upstream server"
            raise HTTPException(status_code=resp.status_code, detail=error_detail)
        
        if raw:
            return resp.content

        return resp.json()
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail=f"Upstream server unavailable: {exc}")

async def update_cache_from_origin(key: str, method: str, path: str, json_data: Optional[dict] = None, page: int = None, limit: int = None):
    try:
        client = http_client
        url = f"{REGISTRY_URL}{path}"
        if method == "GET":
            resp = await client.get(url)
        else:
            return

        if resp.status_code == 200:
            data_bytes = resp.content
            data_str = data_bytes.decode("utf-8")
            
            cache_entry = {
                "payload": data_str, 
                "is_raw": True,
                "timestamp": time.time()
            }
            await redis_client.set(key, json.dumps(cache_entry))
            print(f"Background update success for {key}")
    except Exception as e:
        print(f"Background update failed: {e}")

async def proxy_request(request: Request, background_tasks: BackgroundTasks, method: str, path: str, json_data: Optional[dict] = None, page: int = None, limit: int = None):
    cache_key = f"{method}:{path}"
    
    if method == "GET":
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                background_tasks.add_task(update_cache_from_origin, cache_key, method, path, json_data, page, limit)
                try:
                    cached_obj = json.loads(cached)
                    if isinstance(cached_obj, dict) and "payload" in cached_obj:
                        data = cached_obj["payload"]
                        is_raw = cached_obj.get("is_raw", False)
                        if is_raw:
                            return Response(content=data, media_type="application/json")
                        return data
                    
                    data = cached_obj
                    if isinstance(data, list) and page is not None and limit is not None:
                        return paginate_data(data, page, limit)
                    return data
                except Exception as e:
                    print(f"Cache parse error: {e}")
        except Exception as e:
            print(f"Redis error (get): {e}")
    
    result_raw = await forward_request(method, path, json_data, headers=None, raw=True)
    
    if method == "GET":
        try:
            payload_str = result_raw.decode("utf-8")
            cache_entry = {
                "payload": payload_str, 
                "is_raw": True,
                "timestamp": time.time()
            }
            await redis_client.set(cache_key, json.dumps(cache_entry)) 
        except Exception as e:
            print(f"Redis error (set): {e}")
            
    return Response(content=result_raw, media_type="application/json")

@app.get("/api/requests")
@limiter.limit("100/second")
async def get_requests(
    request: Request, 
    background_tasks: BackgroundTasks, 
    page: PageNumber = 1, 
    limit: PageLimit = 50,
    status: Optional[SafeString] = Query(None),
    search: Optional[SafeString] = Query(None),
    region: Optional[SafeString] = Query(None),
    sort_by: SafeString = "default",
    order: SafeString = "desc"
):
    path = f"/api/requests?page={page}&limit={limit}&sort_by={sort_by}&order={order}"
    if status: path += f"&status={status}"
    if search: path += f"&search={search}"
    if region: path += f"&region={region}"
    return await proxy_request(request, background_tasks, "GET", path, page=page, limit=limit)

@app.get("/api/news")
@limiter.limit("100/second")
async def get_news(
    request: Request, 
    background_tasks: BackgroundTasks, 
    page: PageNumber = 1, 
    limit: PageLimit = 50,
    search: Optional[SafeString] = Query(None),
    sort_by: SafeString = "timestamp",
    order: SafeString = "desc"
):
    path = f"/api/news?page={page}&limit={limit}&sort_by={sort_by}&order={order}"
    if search: path += f"&search={search}"
    return await proxy_request(request, background_tasks, "GET", path, page=page, limit=limit)

@app.get("/api/phones")
@limiter.limit("100/second")
async def get_phones(
    request: Request, 
    background_tasks: BackgroundTasks, 
    page: PageNumber = 1, 
    limit: PageLimit = 50,
    search: Optional[SafeString] = Query(None),
    sort_by: SafeString = "_id",
    order: SafeString = "desc"
):
    path = f"/api/phones?page={page}&limit={limit}&sort_by={sort_by}&order={order}"
    if search: path += f"&search={search}"
    return await proxy_request(request, background_tasks, "GET", path, page=page, limit=limit)

@app.get("/api/rescue_points")
@limiter.limit("100/second")
async def get_rescue_points(
    request: Request, 
    background_tasks: BackgroundTasks, 
    page: PageNumber = 1, 
    limit: PageLimit = 50,
    search: Optional[SafeString] = Query(None),
    sort_by: SafeString = "_id",
    order: SafeString = "desc"
):
    path = f"/api/rescue_points?page={page}&limit={limit}&sort_by={sort_by}&order={order}"
    if search: path += f"&search={search}"
    return await proxy_request(request, background_tasks, "GET", path, page=page, limit=limit)

@app.get("/api/registry/list")
async def list_proxies(include_unsafe: bool = Query(False)):
    proxies_list = []
    try:
        registry_data = await redis_client.hgetall("registry")
        for url, json_str in registry_data.items():
            try:
                data = json.loads(json_str)
                proxies_list.append(data)
            except: continue
    except: pass
    return {"proxies": proxies_list}

@app.get("/api/speedtest")
async def speed_test(request: Request):
    start_time = time.time()
    redis_ping_start = time.time()
    try:
        await redis_client.ping()
        redis_ping = (time.time() - redis_ping_start) * 1000
    except: redis_ping = -1

    hot_start = time.time()
    try:
        await http_client.get(f"{MY_URL}/api/news?page=1&limit=10")
        hot_latency = (time.time() - hot_start) * 1000
    except: hot_latency = -1

    cold_start = time.time()
    try:
        await http_client.get(f"{REGISTRY_URL}/api/news?page=1&limit=10")
        cold_latency = (time.time() - cold_start) * 1000
    except: cold_latency = -1

    total_latency = (time.time() - start_time) * 1000
    return {
        "message": "Speed test results",
        "redis_ping_ms": round(redis_ping, 2),
        "hot_latency_ms": round(hot_latency, 2),
        "cold_latency_ms": round(cold_latency, 2),
        "total_processing_ms": round(total_latency, 2),
        "server": "community-server"
    }

async def background_self_registration():
    print(f"Starting Community Registration Task (Target: {REGISTRY_URL})...")
    while True:
        try:
            # Gather contact info from env
            params = {
                "url": MY_URL, 
                "name": os.getenv("NODE_NAME", "Community Node"), 
                "tag": "Community",
                "zalo": os.getenv("CONTACT_ZALO", ""),
                "phone": os.getenv("CONTACT_PHONE", ""),
                "email": os.getenv("CONTACT_EMAIL", ""),
                "contact_name": os.getenv("CONTACT_NAME", ""),
                "facebook": os.getenv("CONTACT_FB", "")
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{REGISTRY_URL}/api/registry/register", 
                    params=params
                )
                if resp.status_code == 200:
                    print(f"Registration success: {resp.json()}")
                else:
                    print(f"Registration failed with status {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"Registration failed: {e}")
        await asyncio.sleep(30)

@app.on_event("startup")
async def startup_event():
    global http_client
    http_client = httpx.AsyncClient(timeout=30.0, limits=httpx.Limits(max_keepalive_connections=20, max_connections=100))
    asyncio.create_task(background_self_registration())

@app.on_event("shutdown")
async def shutdown_event():
    global http_client
    if http_client:
        await http_client.aclose()

@app.get("/")
async def root():
    return {
        "message": "SOS.INFO.VN - Community Node", 
        "status": "running",
        "name": os.getenv("NODE_NAME", "Community Node")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
