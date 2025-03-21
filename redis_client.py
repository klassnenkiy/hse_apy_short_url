import redis.asyncio as redis
from config import settings

redis_client = redis.from_url(settings.REDIS_URL)

async def get_redis():
    return redis_client

async def get_redis_safe():
    try:
        return await get_redis()
    except Exception as e:
        print(f"Redis connection error: {e}")
        return None