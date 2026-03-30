import json
import time
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from wiki_trending_agent.db import get_session
from wiki_trending_agent.services.events import TERMINAL_EVENTS, get_run_events_since
from wiki_trending_agent.services.ingest import ingest_csv_directory
from wiki_trending_agent.services.orchestrator import create_run, get_run, process_run_by_id
from wiki_trending_agent.services.trends import get_available_hours

app = FastAPI()


class RunCreateRequest(BaseModel):
    hour: datetime
    top_k_pages: int | None = Field(default=None, ge=1)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ingest/csv")
def ingest_csv(
    path: str = Query(..., description="Directory containing CSV files"),
    session: Session = Depends(get_session),
) -> dict[str, int]:
    inserted = ingest_csv_directory(session, Path(path))
    return {"inserted": inserted}


@app.get("/hours")
def list_hours(session: Session = Depends(get_session)) -> dict[str, list[str]]:
    hours = [dt.isoformat() for dt in get_available_hours(session)]
    return {"hours": hours}


@app.post("/runs", status_code=201)
def create_analysis_run(
    payload: RunCreateRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> dict[str, str | int | None]:
    run = create_run(session, payload.hour)
    background_tasks.add_task(process_run_by_id, run.id, payload.top_k_pages)
    return {
        "run_id": run.id,
        "status": run.status,
        "top_k_pages": payload.top_k_pages,
    }


@app.get("/runs/{run_id}")
def get_analysis_run(run_id: str, session: Session = Depends(get_session)) -> dict[str, str]:
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "run_id": run.id,
        "status": run.status,
        "hour": run.hour.isoformat(),
    }


@app.get("/runs/{run_id}/stream")
def stream_analysis_run(run_id: str, session: Session = Depends(get_session)) -> StreamingResponse:
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    def event_generator() -> Iterator[str]:
        index = 0
        max_wait_seconds = 120
        start = time.monotonic()

        while True:
            new_events, index = get_run_events_since(run_id, index)
            for event_type, payload in new_events:
                yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
                if event_type in TERMINAL_EVENTS:
                    return

            if time.monotonic() - start > max_wait_seconds:
                return

            time.sleep(0.2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
