import redis.asyncio as redis
from config import settings

redis_client = redis.from_url(settings.REDIS_URL)

try:
    redis_client = redis.from_url(settings.REDIS_URL)
except Exception as e:
    print(f"Failed to create Redis client: {e}")
    redis_client = None


async def get_redis():
    if redis_client is None:
        raise Exception("Redis client is not available")
    return redis_client


async def get_redis_safe():
    try:
        return await get_redis()
    except Exception as e:
        print(f"Redis connection error: {e}")
        return None
