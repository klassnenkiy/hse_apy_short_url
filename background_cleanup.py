import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import async_session
from models import Link, LinkArchive, User
from email.mime.text import MIMEText
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.header import Header
from config import settings

UNUSED_LINKS_DAYS = 30
WARN_BEFORE_HOURS = 24


async def cleanup_expired_links(db: AsyncSession):
    now = datetime.utcnow()

    result = await db.execute(
        select(Link).where(Link.expires_at != None, Link.expires_at < now)
    )
    expired_links = result.scalars().all()

    for link in expired_links:
        if getattr(link, "auto_renew", False):
            link.expires_at = now + timedelta(days=7)
        else:
            archived = LinkArchive(
                link_id=link.id,
                short_code=link.short_code,
                original_url=link.original_url,
                reason="expired"
            )
            db.add(archived)
            await db.delete(link)

    cutoff = now - timedelta(days=UNUSED_LINKS_DAYS)
    result = await db.execute(select(Link).where(
        ((Link.last_visited != None) & (Link.last_visited < cutoff)) |
        ((Link.last_visited == None) & (Link.created_at < cutoff))
    ))
    unused_links = result.scalars().all()

    for link in unused_links:
        archived = LinkArchive(
            link_id=link.id,
            short_code=link.short_code,
            original_url=link.original_url,
            reason="unused"
        )
        db.add(archived)
        await db.delete(link)
    await db.commit()


async def warn_expiring_links(db: AsyncSession):
    now = datetime.utcnow()
    soon = now + timedelta(hours=WARN_BEFORE_HOURS)

    result = await db.execute(
        select(Link)
        .where(Link.expires_at != None)
        .where(Link.expires_at > now)
        .where(Link.expires_at < soon)
    )
    expiring_links = result.scalars().all()
    for link in expiring_links:
        if link.user_id:
            user = await db.get(User, link.user_id)
            if user and user.email:
                await send_warning_email(user.email, link)


async def send_warning_email(email_to: str, link: Link):
    """
    Асинхронная отправка письма о скором истечении ссылки.
    """
    subject = "Your link is about to expire!"
    body = (f"Hello!\n\nYour link with short code '{link.short_code}' will expire at {link.expires_at}.\n"
            f"Please renew it if you still need it.\n\nRegards,\nYour Link Shortener")

    sender_email = settings.SENDER_EMAIL

    message = MIMEMultipart("alternative")
    message["Subject"] = Header(subject, "utf-8")
    message["From"] = sender_email
    message["To"] = email_to

    text_part = MIMEText(body, "plain", "utf-8")
    message.attach(text_part)

    smtp_hostname = settings.SMTP_HOST
    smtp_port = settings.SMTP_PORT
    smtp_username = settings.SMTP_USERNAME
    smtp_password = settings.SMTP_PASSWORD

    try:
        await aiosmtplib.send(
            message,
            hostname=smtp_hostname,
            port=smtp_port,
            username=smtp_username,
            password=smtp_password,
            start_tls=True,
        )
        print(f"[{datetime.utcnow()}] Email sent to {email_to}")
    except Exception as e:
        print(f"[{datetime.utcnow()}] Failed to send email: {e}")


async def scheduler():
    while True:
        async with async_session() as db:
            await warn_expiring_links(db)
            await cleanup_expired_links(db)
        await asyncio.sleep(60)
