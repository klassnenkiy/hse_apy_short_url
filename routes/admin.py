from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from auth import get_current_admin_user
from models import Link, User
from database import get_db

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/links")
async def get_all_links(db: AsyncSession = Depends(get_db), admin_user=Depends(get_current_admin_user)):
    """
    Возвращает все ссылки в системе (только для admin)
    """
    result = await db.execute(select(Link))
    links = result.scalars().all()
    return links

@router.delete("/links/{link_id}")
async def admin_delete_link(link_id: int, db: AsyncSession = Depends(get_db), admin_user=Depends(get_current_admin_user)):
    """
    Удаление любой ссылки админом
    """
    link_obj = (await db.execute(select(Link).where(Link.id == link_id))).scalars().first()
    if not link_obj:
        raise HTTPException(status_code=404, detail="Link not found")
    await db.delete(link_obj)
    await db.commit()
    return {"detail": f"Link {link_id} deleted by admin"}

@router.get("/users")
async def get_all_users(db: AsyncSession = Depends(get_db), admin_user=Depends(get_current_admin_user)):
    """
    Список пользователей
    """
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users
