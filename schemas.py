from datetime import datetime
from pydantic import BaseModel, HttpUrl, Field, EmailStr
from typing import Optional


class LinkBase(BaseModel):
    original_url: HttpUrl
    expires_at: Optional[datetime] = None
    project: Optional[str] = None


class LinkCreate(LinkBase):
    custom_alias: Optional[str] = None


class LinkUpdate(BaseModel):
    original_url: Optional[HttpUrl] = None
    expires_at: Optional[datetime] = None
    project: Optional[str] = None


class LinkOut(BaseModel):
    short_code: str
    original_url: HttpUrl
    created_at: datetime
    expires_at: Optional[datetime] = None
    project: Optional[str] = None
    visits: int
    last_visited: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str]
    created_at: datetime
    role: Optional[str]

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
