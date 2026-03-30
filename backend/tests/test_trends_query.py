from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from wiki_trending_agent.models import Base, RawHourlyTrend
from wiki_trending_agent.services.trends import get_top_pages_for_hour


def test_select_top_pages_for_hour() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    hour = datetime.fromisoformat("2026-03-29 12:00:00")
    with Session(engine) as session:
        session.add_all(
            [
                RawHourlyTrend(
                    dt=hour,
                    project="en.wikipedia",
                    identifier=1,
                    title="High_Zscore",
                    absolute_views_current=100,
                    absolute_views_zscore=10.0,
                    views_proportion_current=0.01,
                    views_proportion_zscore=5.0,
                ),
                RawHourlyTrend(
                    dt=hour,
                    project="en.wikipedia",
                    identifier=2,
                    title="No_Zscore_Higher_Views",
                    absolute_views_current=500,
                    absolute_views_zscore=None,
                    views_proportion_current=0.05,
                    views_proportion_zscore=None,
                ),
                RawHourlyTrend(
                    dt=hour,
                    project="en.wikipedia",
                    identifier=3,
                    title="Lower_Zscore",
                    absolute_views_current=200,
                    absolute_views_zscore=2.0,
                    views_proportion_current=0.02,
                    views_proportion_zscore=1.0,
                ),
            ]
        )
        session.commit()

        pages = get_top_pages_for_hour(session, hour, limit=2)

    assert len(pages) == 2
    # Ordered by absolute_views_current (desc), then zscore, then title
    assert pages[0].title == "No_Zscore_Higher_Views"
    assert pages[1].title == "Lower_Zscore"
