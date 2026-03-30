from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from wiki_trending_agent.models import Base, RawHourlyTrend
from wiki_trending_agent.services.ingest import ingest_csv_directory


def test_ingests_csv_directory(tmp_path: Path) -> None:
    csv_path = tmp_path / "12.csv"
    csv_path.write_text(
        "dt,project,identifier,title,absolute_views_current,absolute_views_zscore,views_proportion_current,views_proportion_zscore\n"
        "2026-03-29 12:00:00.000,en.wikipedia,1,Example_Page,100,3.5,0.1,2.0\n",
        encoding="utf-8",
    )

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        count = ingest_csv_directory(session, tmp_path)
        rows = session.scalars(select(RawHourlyTrend)).all()

    assert count == 1
    assert len(rows) == 1
    assert rows[0].title == "Example_Page"
