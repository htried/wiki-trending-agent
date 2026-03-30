from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from wiki_trending_agent.models import RawHourlyTrend


def get_available_hours(session: Session) -> list[datetime]:
    stmt = (
        select(RawHourlyTrend.dt)
        .distinct()
        .order_by(desc(RawHourlyTrend.dt))
    )
    return list(session.scalars(stmt).all())


def get_top_pages_for_hour(
    session: Session,
    hour: datetime,
    limit: int | None = 20,
) -> list[RawHourlyTrend]:
    stmt = (
        select(RawHourlyTrend)
        .where(RawHourlyTrend.dt == hour)
        .order_by(
            desc(RawHourlyTrend.absolute_views_current),
            desc(RawHourlyTrend.absolute_views_zscore).nulls_last(),
            RawHourlyTrend.title,
        )
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(session.scalars(stmt).all())
