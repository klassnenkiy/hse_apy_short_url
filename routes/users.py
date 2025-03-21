from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from schemas import UserCreate, UserOut, Token
from models import User
from database import get_db
from auth import get_password_hash, authenticate_user, create_access_token, get_current_user
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from config import settings
from sqlalchemy.future import select

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/register", response_model=UserOut)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == user.username))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    if user.email:
        result = await db.execute(select(User).where(User.email == user.email))
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(username=user.username, email=user.email, password_hash=get_password_hash(user.password))
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Возвращаем информацию о текущем пользователе
    """
    return current_user


@router.post("/create_admin", response_model=UserOut)
async def create_admin(user: UserCreate, db: AsyncSession = Depends(get_db)):
    existing_admin = await db.execute(select(User).where(User.role == "admin"))
    admin = existing_admin.scalars().first()
    if admin:
        raise HTTPException(status_code=400, detail="Admin already exists")

    new_user = User(
        username=user.username,
        email=user.email,
        password_hash=get_password_hash(user.password),
        role="admin"
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
