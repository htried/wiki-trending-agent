from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from wiki_trending_agent.config import settings
from wiki_trending_agent.db import SessionLocal
from wiki_trending_agent.integrations.serper_client import SerperClient
from wiki_trending_agent.integrations.wikimedia_client import WikimediaStructuredContentClient
from wiki_trending_agent.models import AnalysisRun, PageReasoning, RunEvent, RunPage
from wiki_trending_agent.services.agent_runtime import analyze_page_with_agent
from wiki_trending_agent.services.events import record_run_event
from wiki_trending_agent.services.trends import get_top_pages_for_hour


def create_run(session: Session, hour: datetime) -> AnalysisRun:
    run = AnalysisRun(hour=hour, status="queued")
    session.add(run)
    session.commit()
    session.refresh(run)
    record_run_event(run.id, "RUN_QUEUED", {"run_id": run.id, "status": run.status})
    return run


def get_run(session: Session, run_id: str) -> AnalysisRun | None:
    stmt = select(AnalysisRun).where(AnalysisRun.id == run_id)
    return session.scalar(stmt)


def process_run(session: Session, run: AnalysisRun, max_pages: int | None = None) -> AnalysisRun:
    run.status = "running"
    run.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session.commit()
    record_run_event(run.id, "RUN_STARTED", {"run_id": run.id, "status": run.status})

    serper_client = SerperClient(settings.serper_api_key) if settings.serper_api_key else None
    wikimedia_client = (
        WikimediaStructuredContentClient(settings.wikimedia_enterprise_api_key)
        if settings.wikimedia_enterprise_api_key
        else None
    )

    pages = get_top_pages_for_hour(session=session, hour=run.hour, limit=max_pages)
    record_run_event(run.id, "PAGES_SELECTED", {"run_id": run.id, "count": len(pages)})

    for idx, page in enumerate(pages, start=1):
        session.add(
            RunPage(
                run_id=run.id,
                title=page.title,
                absolute_views_current=page.absolute_views_current,
                absolute_views_zscore=page.absolute_views_zscore,
                rank=idx,
            )
        )
        result = analyze_page_with_agent(
            page_title=page.title,
            hour=run.hour,
            serper_client=serper_client,
            wikimedia_client=wikimedia_client,
            emit=lambda event_type, payload: record_run_event(
                run.id, event_type, {"run_id": run.id, "page_title": page.title, **payload}
            ),
        )
        session.add(
            PageReasoning(
                run_id=run.id,
                page_title=page.title,
                reason=str(result.get("reason", "")),
                confidence=float(result.get("confidence", 0.0)),
                evidence={"citations": result.get("citations", [])},
            )
        )
        record_run_event(
            run.id,
            "REASONING_DONE",
            {
                "run_id": run.id,
                "page_title": page.title,
                "reason": result.get("reason", ""),
                "confidence": result.get("confidence", 0.0),
            },
        )
        event_candidate = str(result.get("event_candidate", "")).strip()
        if event_candidate:
            session.add(
                RunEvent(
                    run_id=run.id,
                    event_name=event_candidate[:255],
                    description=event_candidate,
                    confidence=float(result.get("confidence", 0.0)),
                )
            )
            record_run_event(
                run.id,
                "EVENTS_SYNTHESIZED",
                {"run_id": run.id, "event_name": event_candidate},
            )

    run.status = "completed"
    run.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session.commit()
    record_run_event(run.id, "RUN_COMPLETED", {"run_id": run.id, "status": run.status})
    return run


def process_run_by_id(run_id: str, max_pages: int | None = None) -> None:
    with SessionLocal() as session:
        run = get_run(session, run_id)
        if run is None:
            return
        try:
            process_run(session=session, run=run, max_pages=max_pages)
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            run.status = "failed"
            run.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
            run.error_summary = str(exc)
            session.commit()
            record_run_event(
                run.id,
                "RUN_ERROR",
                {"run_id": run.id, "error": str(exc)},
            )
