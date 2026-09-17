from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from wiki_trending_agent.models import RawHourlyTrend

ROW_GEO_PATTERN = re.compile(
    r"Row\(country_code='(?P<country>[A-Z]{2})',\s*percentage=(?P<share>[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\)"
)


def _to_optional_float(raw_value: str) -> float | None:
    return float(raw_value) if raw_value else None


def _to_int(raw_value: str) -> int:
    # Some upstream exports serialize integer ids as decimal strings (e.g. "1388842.0").
    return int(float(raw_value))


def _parse_geo_distribution(
    raw_value: str | None,
) -> list[dict[str, float | str]]:
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, list):
        out: list[dict[str, float | str]] = []
        for item in parsed:
            pair: object = item
            if isinstance(item, str):
                try:
                    pair = json.loads(item)
                except json.JSONDecodeError:
                    continue
            if not isinstance(pair, list) or len(pair) != 2:
                continue
            country, proportion = pair
            if not isinstance(country, str):
                continue
            try:
                proportion_float = float(proportion)
            except (TypeError, ValueError):
                continue
            out.append({"country_code": country, "proportion": proportion_float})
        if out:
            return out
    elif parsed is not None:
        return []

    # Fallback for SQLLab stringified struct format:
    # [Row(country_code='US', percentage=0.67), ...]
    out: list[dict[str, float | str]] = []
    for match in ROW_GEO_PATTERN.finditer(raw_value):
        try:
            share = float(match.group("share"))
        except (TypeError, ValueError):
            continue
        out.append(
            {"country_code": match.group("country"), "proportion": share}
        )
    return out


def ingest_csv_directory(session: Session, data_dir: Path) -> int:
    inserted = 0
    csv_files = sorted(data_dir.glob("*.csv"))

    for csv_file in csv_files:
        with csv_file.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                try:
                    dt_value = datetime.fromisoformat(row["dt"])
                    identifier = _to_int(row["identifier"])
                    absolute_views_current = _to_int(row["absolute_views_current"])
                    absolute_views_zscore = _to_optional_float(row["absolute_views_zscore"])
                    views_proportion_current = float(row["views_proportion_current"])
                    views_proportion_zscore = _to_optional_float(
                        row["views_proportion_zscore"]
                    )
                except (KeyError, TypeError, ValueError):
                    # Skip malformed rows rather than failing the full ingest request.
                    continue

                exists_stmt = select(
                    exists().where(
                        RawHourlyTrend.dt == dt_value,
                        RawHourlyTrend.project == row["project"],
                        RawHourlyTrend.identifier == identifier,
                        RawHourlyTrend.title == row["title"],
                    )
                )
                if session.scalar(exists_stmt):
                    continue

                session.add(
                    RawHourlyTrend(
                        dt=dt_value,
                        project=row["project"],
                        identifier=identifier,
                        title=row["title"],
                        absolute_views_current=absolute_views_current,
                        absolute_views_zscore=absolute_views_zscore,
                        views_proportion_current=views_proportion_current,
                        views_proportion_zscore=views_proportion_zscore,
                        geo_distribution=_parse_geo_distribution(
                            row.get("geo_distribution")
                        ),
                    )
                )
                inserted += 1

    session.commit()
    return inserted
