import redis.asyncio as redis
from config import settings

redis_client = redis.from_url(settings.REDIS_URL)

async def get_redis():
    return redis_client