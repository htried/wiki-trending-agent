from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RawHourlyTrend(Base):
    __tablename__ = "raw_hourly_trends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dt: Mapped[datetime] = mapped_column(DateTime(timezone=False), index=True)
    project: Mapped[str] = mapped_column(String(100), index=True)
    identifier: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(512), index=True)
    absolute_views_current: Mapped[int] = mapped_column(Integer)
    absolute_views_zscore: Mapped[float | None] = mapped_column(Float, nullable=True)
    views_proportion_current: Mapped[float] = mapped_column(Float)
    views_proportion_zscore: Mapped[float | None] = mapped_column(Float, nullable=True)


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    hour: Mapped[datetime] = mapped_column(DateTime(timezone=False), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class RunPage(Base):
    __tablename__ = "run_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    title: Mapped[str] = mapped_column(String(512), index=True)
    absolute_views_current: Mapped[int] = mapped_column(Integer)
    absolute_views_zscore: Mapped[float | None] = mapped_column(Float, nullable=True)
    rank: Mapped[int] = mapped_column(Integer)


class PageNewsHit(Base):
    __tablename__ = "page_news_hits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    page_title: Mapped[str] = mapped_column(String(512), index=True)
    source_name: Mapped[str] = mapped_column(String(255))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)


class PageWikiContent(Base):
    __tablename__ = "page_wiki_content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    page_title: Mapped[str] = mapped_column(String(512), index=True)
    revision: Mapped[str | None] = mapped_column(String(128), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)
    content_json: Mapped[dict[str, Any]] = mapped_column(JSON)


class PageReasoning(Base):
    __tablename__ = "page_reasoning"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    page_title: Mapped[str] = mapped_column(String(512), index=True)
    reason: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class RunEvent(Base):
    __tablename__ = "run_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    event_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
