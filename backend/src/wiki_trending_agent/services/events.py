from __future__ import annotations

import json
from collections.abc import Iterator
from threading import Lock
from typing import Any

_store_lock = Lock()
_run_events: dict[str, list[tuple[str, dict[str, Any]]]] = {}
TERMINAL_EVENTS = {"RUN_COMPLETED", "RUN_ERROR"}


def _sse_event(event_type: str, payload: dict[str, Any]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"


def record_run_event(run_id: str, event_type: str, payload: dict[str, Any]) -> None:
    with _store_lock:
        _run_events.setdefault(run_id, []).append((event_type, payload))


def get_run_events_since(
    run_id: str,
    start_index: int,
) -> tuple[list[tuple[str, dict[str, Any]]], int]:
    with _store_lock:
        run_events = _run_events.get(run_id, [])
        new_events = list(run_events[start_index:])
        end_index = len(run_events)
    return new_events, end_index


def iter_run_events(run_id: str) -> Iterator[str]:
    run_events, _ = get_run_events_since(run_id, 0)
    for event_type, payload in run_events:
        yield _sse_event(event_type, payload)
