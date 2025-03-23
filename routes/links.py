import string
import random
import json
import logging
from datetime import timedelta, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Link, User, LinkVisit, LinkArchive
from schemas import LinkCreate, LinkOut, LinkUpdate
from database import get_db
from auth import get_current_user_optional, get_current_user
from redis_client import get_redis
from typing import List

router = APIRouter(prefix="/links", tags=["links"])

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def generate_short_code(length: int = 6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


async def clear_link_cache(link: Link):
    try:
        redis = await get_redis()
        await redis.delete(f"link:{link.short_code}")
        await redis.delete(f"search:{link.original_url}")
    except Exception as e:
        logger.warning(f"Failed to clear cache for link {link.short_code}: {e}")



@router.get("/search")
async def search_link(original_url: str, db: AsyncSession = Depends(get_db)):
    try:
        redis = await get_redis()
        cached = await redis.get(f"search:{original_url}")
        if cached:
            return json.loads(cached)
    except Exception as e:
        print(f"Redis error in search cache: {e}")
    result = await db.execute(select(Link).where(Link.original_url == original_url))
    link_obj = result.scalars().first()
    if not link_obj:
        raise HTTPException(status_code=404, detail="Link not found")

    data = {"short_code": link_obj.short_code, "original_url": link_obj.original_url}
    try:
        if redis:
            await redis.set(f"search:{original_url}", json.dumps(data), ex=60 * 10)
    except Exception as e:
        print(f"Error setting redis cache for search: {e}")
    return data


@router.post("/shorten", response_model=LinkOut)
async def create_link(link: LinkCreate,
                      db: AsyncSession = Depends(get_db),
                      current_user=Depends(get_current_user_optional)):
    logger.info(f"Creating new link with original URL: {link.original_url}")

    if link.custom_alias:
        result = await db.execute(select(Link).where(Link.custom_alias == link.custom_alias))
        existing = result.scalars().first()
        if existing:
            raise HTTPException(status_code=400, detail="Custom alias already exists")
        short_code = link.custom_alias
    else:
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

    logger.info(f"New link created with short code: {short_code}")
    return new_link


@router.get("/my", response_model=List[LinkOut])
async def get_my_links(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Link).where(Link.user_id == current_user.id))
    links = result.scalars().all()
    return links


@router.get("/{short_code}")
async def redirect_link(short_code: str,
                        request: Request,
                        db: AsyncSession = Depends(get_db)):
    try:
        redis = await get_redis()
        cached = await redis.get(f"link:{short_code}")
    except Exception as e:
        print(f"Redis error: {e}")
        cached = None

    result = await db.execute(select(Link).where(Link.short_code == short_code))
    link_obj = result.scalars().first()
    if not link_obj:
        raise HTTPException(status_code=404, detail="Link not found")
    if link_obj.expires_at and datetime.now(timezone.utc) > link_obj.expires_at:
        raise HTTPException(status_code=410, detail="Link expired")

    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")

    now = datetime.utcnow()
    day_str = now.strftime("%Y-%m-%d")
    hour_str = now.strftime("%Y-%m-%d-%H")

    from models import LinkVisit
    visit = LinkVisit(
        link_id=link_obj.id,
        visited_at=now,
        day_str=day_str,
        hour_str=hour_str,
        ip=client_ip,
        user_agent=user_agent
    )
    db.add(visit)

    link_obj.visits += 1
    link_obj.last_visited = now
    await db.commit()

    if not cached:
        await redis.set(f"link:{short_code}", json.dumps({"original_url": link_obj.original_url}), ex=60 * 60)

    return Response(status_code=307, headers={"Location": link_obj.original_url})


@router.delete("/{short_code}")
async def delete_link(
        short_code: str,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user_optional)
):
    logger.info(f"Deleting link with short code: {short_code}")

    result = await db.execute(select(Link).where(Link.short_code == short_code))
    link_obj = result.scalars().first()
    if not link_obj:
        raise HTTPException(status_code=404, detail="Link not found")

    if link_obj.user_id is not None:
        if not current_user or link_obj.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

    archived = LinkArchive(
        link_id=link_obj.id,
        short_code=link_obj.short_code,
        original_url=link_obj.original_url,
        reason="user"
    )
    db.add(archived)

    await db.delete(link_obj)
    await db.commit()
    await clear_link_cache(link_obj)
    logger.info(f"Link with short code {short_code} deleted and archived.")
    return {"detail": "Link archived and deleted successfully"}


@router.put("/{short_code}", response_model=LinkOut)
async def update_link(short_code: str,
                      link_update: LinkUpdate,
                      db: AsyncSession = Depends(get_db),
                      current_user=Depends(get_current_user_optional)):
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
    await clear_link_cache(link_obj)
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


@router.get("/{short_code}/analytics/daily")
async def link_analytics_daily(short_code: str, db: AsyncSession = Depends(get_db)):
    redis = await get_redis()
    cache_key = f"analytics:daily:{short_code}"
    cached_data = await redis.get(cache_key)
    if cached_data:
        logger.info(f"Cache hit for daily analytics of {short_code}")
        return json.loads(cached_data)
    logger.info(f"Cache miss for daily analytics of {short_code}")
    result = await db.execute(select(Link).where(Link.short_code == short_code))
    link_obj = result.scalars().first()
    if not link_obj:
        raise HTTPException(status_code=404, detail="Link not found")
    stmt = select(
        LinkVisit.day_str,
        func.count(LinkVisit.id)
    ).where(LinkVisit.link_id == link_obj.id) \
        .group_by(LinkVisit.day_str) \
        .order_by(LinkVisit.day_str)

    result = await db.execute(stmt)
    rows = result.all()

    data = [{"day": row[0], "count": row[1]} for row in rows]

    await redis.set(cache_key, json.dumps(data), ex=3600)

    return data


@router.get("/{short_code}/analytics/hourly")
async def link_analytics_hourly(short_code: str, db: AsyncSession = Depends(get_db)):
    from models import LinkVisit
    link_obj = (await db.execute(select(Link).where(Link.short_code == short_code))).scalars().first()
    if not link_obj:
        raise HTTPException(status_code=404, detail="Link not found")

    stmt = select(
        LinkVisit.hour_str,
        func.count(LinkVisit.id)
    ).where(LinkVisit.link_id == link_obj.id)\
     .group_by(LinkVisit.hour_str)\
     .order_by(LinkVisit.hour_str)

    result = await db.execute(stmt)
    rows = result.all()
    return [{"hour": row[0], "count": row[1]} for row in rows]


@router.get("/{short_code}/analytics/agents")
async def link_analytics_agents(short_code: str, db: AsyncSession = Depends(get_db)):
    """
    Возвращаем топ User-Agent с подсчётом переходов
    """
    from models import LinkVisit
    link_obj = (await db.execute(select(Link).where(Link.short_code == short_code))).scalars().first()
    if not link_obj:
        raise HTTPException(status_code=404, detail="Link not found")

    stmt = select(
        LinkVisit.user_agent,
        func.count(LinkVisit.id)
    ).where(LinkVisit.link_id == link_obj.id)\
     .group_by(LinkVisit.user_agent)\
     .order_by(func.count(LinkVisit.id).desc())

    result = await db.execute(stmt)
    rows = result.all()
    return [{"user_agent": row[0], "count": row[1]} for row in rows]


@router.get("/project/{project_name}/stats")
async def get_project_stats(project_name: str, db: AsyncSession = Depends(get_db)):
    result_links = await db.execute(select(Link).where(Link.project == project_name))
    links = result_links.scalars().all()
    if not links:
        raise HTTPException(status_code=404, detail="No links found in this project")

    link_ids = [l.id for l in links]

    from models import LinkVisit
    stmt_visits = select(func.count(LinkVisit.id)).where(LinkVisit.link_id.in_(link_ids))
    total_visits = (await db.execute(stmt_visits)).scalar() or 0

    stmt_unique_ips = select(func.count(func.distinct(LinkVisit.ip))).where(LinkVisit.link_id.in_(link_ids))
    unique_ips = (await db.execute(stmt_unique_ips)).scalar() or 0

    return {
        "project_name": project_name,
        "total_visits": total_visits,
        "unique_ips": unique_ips
    }


@router.post("/{short_code}/renew")
async def renew_link(short_code: str,
                     db: AsyncSession = Depends(get_db),
                     current_user=Depends(get_current_user_optional)):
    """
    Явное продление ссылки пользователем.
    """
    result = await db.execute(select(Link).where(Link.short_code == short_code))
    link_obj = result.scalars().first()
    if not link_obj:
        raise HTTPException(status_code=404, detail="Link not found")

    if link_obj.user_id is not None:
        if not current_user or link_obj.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

    now = datetime.now(timezone.utc)
    if link_obj.expires_at and link_obj.expires_at > now:
        link_obj.expires_at = link_obj.expires_at + timedelta(days=7)
    else:
        link_obj.expires_at = now + timedelta(days=7)

    await db.commit()
    await db.refresh(link_obj)
    await clear_link_cache(link_obj)
    return {"detail": "Link renewed", "new_expires_at": link_obj.expires_at}
