from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from wiki_trending_agent.models import Base, RawHourlyTrend  # type: ignore[import-untyped]
from wiki_trending_agent.services.geo_signals import (  # type: ignore[import-untyped]
    compute_geo_signals_for_page,
)


def _trend_row(
    dt: datetime,
    title: str,
    geo_distribution: list[dict[str, float | str]],
) -> RawHourlyTrend:
    return RawHourlyTrend(
        dt=dt,
        project="en.wikipedia",
        identifier=1,
        title=title,
        absolute_views_current=100,
        absolute_views_zscore=1.0,
        views_proportion_current=0.01,
        views_proportion_zscore=1.0,
        geo_distribution=geo_distribution,
    )


def test_detects_notable_country_from_historical_baseline() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    hour = datetime.fromisoformat("2026-03-31 14:00:00")

    with Session(engine) as session:
        for i in range(6):
            session.add(
                _trend_row(
                    dt=hour - timedelta(hours=i + 1),
                    title="Geo_Page",
                    geo_distribution=[
                        {"country_code": "US", "proportion": 0.10 + (i * 0.005)}
                    ],
                )
            )
        session.commit()

        current = _trend_row(
            dt=hour,
            title="Geo_Page",
            geo_distribution=[
                {"country_code": "US", "proportion": 0.60},
                {"country_code": "GB", "proportion": 0.20},
            ],
        )
        result = compute_geo_signals_for_page(session=session, current_page=current)

    assert result["geo_signal_summary"]["status"] == "ok"
    assert len(result["geo_notable_countries"]) == 1
    assert result["geo_notable_countries"][0]["country_code"] == "US"


def test_returns_insufficient_baseline_when_samples_too_low() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    hour = datetime.fromisoformat("2026-03-31 14:00:00")

    with Session(engine) as session:
        session.add(
            _trend_row(
                dt=hour - timedelta(hours=1),
                title="Geo_Page",
                geo_distribution=[{"country_code": "US", "proportion": 0.20}],
            )
        )
        session.commit()
        current = _trend_row(
            dt=hour,
            title="Geo_Page",
            geo_distribution=[{"country_code": "US", "proportion": 0.30}],
        )

        result = compute_geo_signals_for_page(
            session=session, current_page=current, min_samples=5
        )

    assert result["geo_notable_countries"] == []
    assert result["geo_signal_summary"]["status"] == "insufficient_baseline"
