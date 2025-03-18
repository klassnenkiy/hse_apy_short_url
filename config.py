import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "pMRwwlGnPBvFWGHTc-7ulJ9odt4yXd3AysAQbj1AJnY=")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

settings = Settings()

DATABASE_URL = f'postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/short_url'