import string
import random
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Link
from schemas import LinkCreate, LinkOut, LinkUpdate
from database import get_db
from auth import get_current_user_optional
from redis_client import get_redis
from typing import Optional, List

router = APIRouter(prefix="/links", tags=["links"])

def generate_short_code(length: int = 6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


@router.get("/search")
async def search_link(original_url: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Link).where(Link.original_url == original_url))
    link_obj = result.scalars().first()
    if not link_obj:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"short_code": link_obj.short_code, "original_url": link_obj.original_url}


@router.post("/shorten", response_model=LinkOut)
async def create_link(link: LinkCreate,
                      db: AsyncSession = Depends(get_db),
                      current_user = Depends(get_current_user_optional)):
    if link.custom_alias:
        result = await db.execute(select(Link).where(Link.custom_alias == link.custom_alias))
        existing = result.scalars().first()
        if existing:
            raise HTTPException(status_code=400, detail="Custom alias already exists")
        short_code = link.custom_alias
    else:
        short_code = generate_short_code()
        while True:
            result = await db.execute(select(Link).where(Link.short_code == short_code))
            existing = result.scalars().first()
            if not existing:
                break
            short_code = generate_short_code()

    new_link = Link(
        short_code=short_code,
        original_url=str(link.original_url),
        custom_alias=link.custom_alias,
        expires_at=link.expires_at,
        project=link.project,
        user_id=current_user.id if current_user else None
    )
    db.add(new_link)
    await db.commit()
    await db.refresh(new_link)
    return new_link


@router.get("/{short_code}")
async def redirect_link(short_code: str, db: AsyncSession = Depends(get_db)):
    redis = await get_redis()
    cached = await redis.get(f"link:{short_code}")
    if cached:
        data = json.loads(cached)
        stmt = select(Link).where(Link.short_code == short_code)
        result = await db.execute(stmt)
        link_obj = result.scalars().first()
        if link_obj:
            link_obj.visits += 1
            link_obj.last_visited = datetime.utcnow()
            await db.commit()
        return Response(status_code=307, headers={"Location": data["original_url"]})

    result = await db.execute(select(Link).where(Link.short_code == short_code))
    link_obj = result.scalars().first()
    if not link_obj:
        raise HTTPException(status_code=404, detail="Link not found")
    if link_obj.expires_at and datetime.utcnow() > link_obj.expires_at:
        raise HTTPException(status_code=410, detail="Link expired")
    link_obj.visits += 1
    link_obj.last_visited = datetime.utcnow()
    await db.commit()
    await redis.set(f"link:{short_code}", json.dumps({"original_url": link_obj.original_url}), ex=60 * 60)
    return Response(status_code=307, headers={"Location": link_obj.original_url})


@router.delete("/{short_code}")
async def delete_link(short_code: str,
                      db: AsyncSession = Depends(get_db),
                      current_user = Depends(get_current_user_optional)):
    result = await db.execute(select(Link).where(Link.short_code == short_code))
    link_obj = result.scalars().first()
    if not link_obj:
        raise HTTPException(status_code=404, detail="Link not found")
    if link_obj.user_id is not None:
        if not current_user or link_obj.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this link")
    await db.delete(link_obj)
    await db.commit()
    redis = await get_redis()
    await redis.delete(f"link:{short_code}")
    return {"detail": "Link deleted"}


@router.put("/{short_code}", response_model=LinkOut)
async def update_link(short_code: str,
                      link_update: LinkUpdate,
                      db: AsyncSession = Depends(get_db),
                      current_user = Depends(get_current_user_optional)):
    result = await db.execute(select(Link).where(Link.short_code == short_code))
    link_obj = result.scalars().first()
    if not link_obj:
        raise HTTPException(status_code=404, detail="Link not found")
    if link_obj.user_id is not None:
        if not current_user or link_obj.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to update this link")
    if link_update.original_url is not None:
        link_obj.original_url = str(link_update.original_url)
    if link_update.expires_at is not None:
        link_obj.expires_at = link_update.expires_at
    if link_update.project is not None:
        link_obj.project = link_update.project
    await db.commit()
    await db.refresh(link_obj)
    redis = await get_redis()
    await redis.delete(f"link:{short_code}")
    return link_obj


@router.get("/{short_code}/stats", response_model=LinkOut)
async def link_stats(short_code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Link).where(Link.short_code == short_code))
    link_obj = result.scalars().first()
    if not link_obj:
        raise HTTPException(status_code=404, detail="Link not found")
    return link_obj

@router.get("/expired", response_model=List[LinkOut])
async def get_expired_links(db: AsyncSession = Depends(get_db)):
    now = datetime.utcnow()
    result = await db.execute(select(Link).where(Link.expires_at != None, Link.expires_at < now))
    expired_links = result.scalars().all()
    return expired_links

@router.get("/project/{project_name}", response_model=List[LinkOut])
async def get_links_by_project(project_name: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Link).where(Link.project == project_name))
    links = result.scalars().all()
    return links
