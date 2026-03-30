from wiki_trending_agent.models import AnalysisRun, RawHourlyTrend


def test_model_tables_exist() -> None:
    assert RawHourlyTrend.__tablename__ == "raw_hourly_trends"
    assert AnalysisRun.__tablename__ == "analysis_runs"
