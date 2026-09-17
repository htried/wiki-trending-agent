from __future__ import annotations

from datetime import timedelta
from math import sqrt

from sqlalchemy import select
from sqlalchemy.orm import Session

from wiki_trending_agent.models import RawHourlyTrend


def _current_geo_distribution(
    current_page: RawHourlyTrend,
) -> list[dict[str, float | str]]:
    raw = current_page.geo_distribution
    if not isinstance(raw, list):
        return []
    out: list[dict[str, float | str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        country_code = item.get("country_code")
        proportion = item.get("proportion")
        if not isinstance(country_code, str):
            continue
        if not isinstance(proportion, (int, float, str)):
            continue
        try:
            proportion_float = float(proportion)
        except (TypeError, ValueError):
            continue
        out.append({"country_code": country_code, "proportion": proportion_float})
    out.sort(key=lambda row: float(row["proportion"]), reverse=True)
    return out


def _sample_stats(values: list[float]) -> tuple[float, float]:
    mean = sum(values) / len(values)
    if len(values) < 2:
        return mean, 0.0
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return mean, sqrt(max(variance, 0.0))


def compute_geo_signals_for_page(
    session: Session,
    current_page: RawHourlyTrend,
    lookback_days: int = 14,
    min_samples: int = 5,
    min_share_floor: float = 0.05,
    z_threshold: float = 2.0,
) -> dict[str, object]:
    current_distribution = _current_geo_distribution(current_page)
    if not current_distribution:
        return {
            "geo_distribution": [],
            "geo_notable_countries": [],
            "geo_signal_summary": {"status": "no_geo_data", "notable_count": 0},
        }

    lookback_start = current_page.dt - timedelta(days=lookback_days)
    historical_rows = list(
        session.scalars(
            select(RawHourlyTrend).where(
                RawHourlyTrend.title == current_page.title,
                RawHourlyTrend.dt < current_page.dt,
                RawHourlyTrend.dt >= lookback_start,
            )
        ).all()
    )

    by_country: dict[str, list[float]] = {}
    for row in historical_rows:
        row_dist = (
            row.geo_distribution
            if isinstance(row.geo_distribution, list)
            else []
        )
        for item in row_dist:
            if not isinstance(item, dict):
                continue
            code = item.get("country_code")
            prop = item.get("proportion")
            if not isinstance(code, str):
                continue
            if not isinstance(prop, (int, float, str)):
                continue
            try:
                prop_float = float(prop)
            except (TypeError, ValueError):
                continue
            by_country.setdefault(code, []).append(prop_float)

    notable: list[dict[str, float | str | int]] = []
    insufficient_for_any = False
    for item in current_distribution:
        country = str(item["country_code"])
        current_share = float(item["proportion"])
        samples = by_country.get(country, [])
        if len(samples) < min_samples:
            insufficient_for_any = True
            continue

        mean, stddev = _sample_stats(samples)
        zscore = 0.0 if stddev == 0 else (current_share - mean) / stddev
        if current_share >= min_share_floor and zscore >= z_threshold:
            notable.append(
                {
                    "country_code": country,
                    "current_share": current_share,
                    "baseline_mean": mean,
                    "zscore": zscore,
                    "sample_count": len(samples),
                }
            )

    notable.sort(key=lambda row: float(row["zscore"]), reverse=True)
    status = "ok"
    if not notable and insufficient_for_any:
        status = "insufficient_baseline"

    return {
        "geo_distribution": current_distribution,
        "geo_notable_countries": notable,
        "geo_signal_summary": {
            "status": status,
            "notable_count": len(notable),
            "strongest_country_code": (
                notable[0]["country_code"] if notable else None
            ),
        },
    }
