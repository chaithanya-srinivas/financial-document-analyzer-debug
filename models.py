from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db import Base

def _uuid() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    jobs: Mapped[list["Job"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)  # pending|done|error
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped[Optional["User"]] = relationship(back_populates="jobs")
    analysis: Mapped[Optional["Analysis"]] = relationship(back_populates="job", uselist=False, cascade="all, delete-orphan")

class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), unique=True, index=True)
    # store the full JSON result in text (SQLite-friendly)
    result_json: Mapped[str] = mapped_column(Text)

    # convenient columns for quick filters
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    quarter: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recommendation_action: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    confidence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    job: Mapped["Job"] = relationship(back_populates="analysis")