import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import async_session
from models import Link

UNUSED_LINKS_DAYS = 30

async def cleanup_expired_links():
    async with async_session() as db:
        now = datetime.utcnow()
        result = await db.execute(select(Link).where(Link.expires_at != None, Link.expires_at < now))
        expired_links = result.scalars().all()
        for link in expired_links:
            await db.delete(link)
        cutoff = now - timedelta(days=UNUSED_LINKS_DAYS)
        result = await db.execute(select(Link).where(
            ((Link.last_visited != None) & (Link.last_visited < cutoff)) |
            ((Link.last_visited == None) & (Link.created_at < cutoff))
        ))
        unused_links = result.scalars().all()
        for link in unused_links:
            await db.delete(link)
        await db.commit()

async def scheduler():
    while True:
        await cleanup_expired_links()
        await asyncio.sleep(60)
