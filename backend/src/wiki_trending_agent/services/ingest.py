from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from wiki_trending_agent.models import RawHourlyTrend


def _to_optional_float(raw_value: str) -> float | None:
    return float(raw_value) if raw_value else None


def ingest_csv_directory(session: Session, data_dir: Path) -> int:
    inserted = 0
    csv_files = sorted(data_dir.glob("*.csv"))

    for csv_file in csv_files:
        with csv_file.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                dt_value = datetime.fromisoformat(row["dt"])
                exists_stmt = select(
                    exists().where(
                        RawHourlyTrend.dt == dt_value,
                        RawHourlyTrend.project == row["project"],
                        RawHourlyTrend.identifier == int(row["identifier"]),
                        RawHourlyTrend.title == row["title"],
                    )
                )
                if session.scalar(exists_stmt):
                    continue

                session.add(
                    RawHourlyTrend(
                        dt=dt_value,
                        project=row["project"],
                        identifier=int(row["identifier"]),
                        title=row["title"],
                        absolute_views_current=int(row["absolute_views_current"]),
                        absolute_views_zscore=_to_optional_float(row["absolute_views_zscore"]),
                        views_proportion_current=float(row["views_proportion_current"]),
                        views_proportion_zscore=_to_optional_float(row["views_proportion_zscore"]),
                    )
                )
                inserted += 1

    session.commit()
    return inserted
