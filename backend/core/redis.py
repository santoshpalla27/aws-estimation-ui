"""
Redis client configuration
"""

import redis.asyncio as redis
from core.config import settings

# Create Redis client
redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True
)


async def get_redis():
    """Dependency for Redis client"""
    return redis_client
