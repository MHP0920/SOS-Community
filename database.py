"""
Copyright (c) 2025 Nexuron
Licensed under the Nexuron Custom License — see LICENSE.
"""
import os
import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Redis
# Configure connection pool for better performance and keep-alive
pool = redis.ConnectionPool.from_url(REDIS_URL, decode_responses=True, max_connections=20)
redis_client = redis.Redis(connection_pool=pool)

async def get_redis():
    return redis_client
