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


def test_ingests_geo_distribution_column(tmp_path: Path) -> None:
    csv_path = tmp_path / "geo.csv"
    csv_path.write_text(
        "dt,project,identifier,title,absolute_views_current,absolute_views_zscore,views_proportion_current,views_proportion_zscore,geo_distribution\n"
        '2026-03-31 14:00:00.000,en.wikipedia,2,Geo_Page,200,2.5,0.2,1.5,"[[""US"",0.7],[""GB"",0.3]]"\n',
        encoding="utf-8",
    )

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        count = ingest_csv_directory(session, tmp_path)
        row = session.scalars(select(RawHourlyTrend).where(RawHourlyTrend.title == "Geo_Page")).first()

    assert count == 1
    assert row is not None
    assert row.geo_distribution == [{"country_code": "US", "proportion": 0.7}, {"country_code": "GB", "proportion": 0.3}]


def test_ingests_identifier_with_decimal_string(tmp_path: Path) -> None:
    csv_path = tmp_path / "identifier_float.csv"
    csv_path.write_text(
        "dt,project,identifier,title,absolute_views_current,absolute_views_zscore,views_proportion_current,views_proportion_zscore\n"
        "2026-03-31 14:00:00.000,en.wikipedia,1388842.0,Float_Id_Page,120,1.1,0.01,0.5\n",
        encoding="utf-8",
    )

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        count = ingest_csv_directory(session, tmp_path)
        row = session.scalars(select(RawHourlyTrend).where(RawHourlyTrend.title == "Float_Id_Page")).first()

    assert count == 1
    assert row is not None
    assert row.identifier == 1388842


def test_skips_row_with_empty_identifier(tmp_path: Path) -> None:
    csv_path = tmp_path / "empty_identifier.csv"
    csv_path.write_text(
        "dt,project,identifier,title,absolute_views_current,absolute_views_zscore,views_proportion_current,views_proportion_zscore\n"
        "2026-03-31 14:00:00.000,en.wikipedia,,Bad_Row,120,1.1,0.01,0.5\n"
        "2026-03-31 14:00:00.000,en.wikipedia,42,Good_Row,130,1.2,0.02,0.6\n",
        encoding="utf-8",
    )

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        count = ingest_csv_directory(session, tmp_path)
        rows = session.scalars(select(RawHourlyTrend)).all()

    assert count == 1
    assert len(rows) == 1
    assert rows[0].title == "Good_Row"


def test_parses_sqllab_row_style_geo_distribution(tmp_path: Path) -> None:
    csv_path = tmp_path / "sqllab_geo.csv"
    csv_path.write_text(
        "dt,project,identifier,title,absolute_views_current,absolute_views_zscore,views_proportion_current,views_proportion_zscore,geo_distribution\n"
        "\"2026-03-31 14:00:00.000\",en.wikipedia,100,Geo_Row_Format,200,2.5,0.2,1.5,\"[Row(country_code='US', percentage=0.61), Row(country_code='GB', percentage=0.13)]\"\n",
        encoding="utf-8",
    )

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        count = ingest_csv_directory(session, tmp_path)
        row = session.scalars(select(RawHourlyTrend).where(RawHourlyTrend.title == "Geo_Row_Format")).first()

    assert count == 1
    assert row is not None
    assert row.geo_distribution == [
        {"country_code": "US", "proportion": 0.61},
        {"country_code": "GB", "proportion": 0.13},
    ]
