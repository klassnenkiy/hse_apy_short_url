from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy.orm import relationship

Base = declarative_base()


class Link(Base):
    __tablename__ = "links"
    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String(50), unique=True, index=True, nullable=False)
    original_url = Column(Text, nullable=False)
    custom_alias = Column(String(50), unique=True, index=True, nullable=True)
    project = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    visits = Column(Integer, default=0)
    auto_renew = Column(Boolean, default=False)
    last_visited = Column(DateTime(timezone=True), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    visits_rel = relationship("LinkVisit", back_populates="link", cascade="all, delete-orphan", passive_deletes=True)


class LinkVisit(Base):
    __tablename__ = "link_visits"
    id = Column(Integer, primary_key=True, index=True)
    link_id = Column(Integer, ForeignKey("links.id"), nullable=False)
    visited_at = Column(DateTime(timezone=True), default=func.now())
    day_str = Column(String(20), nullable=False)
    hour_str = Column(String(25), nullable=False)
    ip = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    link = relationship("Link", back_populates="visits_rel")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    role = Column(String(20), default="user")


class LinkArchive(Base):
    __tablename__ = "link_archive"
    id = Column(Integer, primary_key=True, index=True)
    link_id = Column(Integer)
    short_code = Column(String(50))
    original_url = Column(Text)
    deleted_at = Column(DateTime(timezone=True), server_default=func.now())
    reason = Column(String(50), nullable=False)
