import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 300
    REDIS_URL: str = os.getenv("REDIS_URL")
    UNUSED_LINKS_DAYS: int = 30

    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "your_address@gmail.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "YOUR_APP_PASSWORD")
    SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", "your_address@gmail.com")



settings = Settings()
