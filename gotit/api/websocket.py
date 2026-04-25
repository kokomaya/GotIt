"""WebSocket endpoint for real-time pipeline communication."""

from __future__ import annotations

import contextlib
import json
from typing import TYPE_CHECKING, Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from gotit.domain.events import (
    DomainEvent,
    ErrorEvent,
    ExecutionEvent,
    IntentEvent,
    SearchEvent,
    TranscriptEvent,
)
from gotit.services.session import SessionRecord

if TYPE_CHECKING:
    from gotit.api.dependencies import _AppState

log = structlog.get_logger()

ws_router = APIRouter()


def _event_to_message(event: DomainEvent) -> dict[str, Any] | None:
    if isinstance(event, TranscriptEvent) and event.transcript:
        return {
            "type": "transcript",
            "data": {
                "text": event.transcript.text,
                "partial": event.partial,
                "language": event.transcript.language,
            },
        }
    if isinstance(event, IntentEvent) and event.intent:
        return {
            "type": "intent",
            "data": {
                "action": event.intent.action,
                "query": event.intent.query,
                "target": event.intent.target,
                "filters": event.intent.filters,
                "confidence": event.intent.confidence,
            },
        }
    if isinstance(event, SearchEvent):
        return {
            "type": "results",
            "data": [
                {
                    "path": r.path,
                    "filename": r.filename,
                    "size": r.size,
                    "modified": r.modified.isoformat() if r.modified else None,
                }
                for r in event.results
            ],
        }
    if isinstance(event, ExecutionEvent) and event.result:
        return {
            "type": "executed",
            "data": {
                "success": event.result.success,
                "action": event.result.action,
                "message": event.result.message,
            },
        }
    if isinstance(event, ErrorEvent):
        return {
            "type": "error",
            "data": {"stage": event.stage, "message": event.message},
        }
    return None


@ws_router.websocket("/ws/pipeline")
async def pipeline_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    state: _AppState = websocket.app.state.app_state
    log.info("ws_connected")

    last_results: list = []

    async def forward_event(event: DomainEvent) -> None:
        nonlocal last_results
        msg = _event_to_message(event)
        if msg:
            if isinstance(event, SearchEvent):
                last_results = event.results
            with contextlib.suppress(Exception):
                await websocket.send_json(msg)

    event_types = [TranscriptEvent, IntentEvent, SearchEvent, ExecutionEvent, ErrorEvent]
    for et in event_types:
        state.event_bus.subscribe(et, forward_event)

    try:
        await websocket.send_json({"type": "state", "data": {"status": "ready"}})

        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "data": {"message": "Invalid JSON"}}
                )
                continue

            msg_type = msg.get("type")
            msg_data = msg.get("data", {})

            if msg_type == "submit_text":
                text = msg_data.get("text", "").strip()
                if not text:
                    await websocket.send_json(
                        {"type": "error", "data": {"message": "Empty text"}}
                    )
                    continue
                last_results = []
                result = await state.pipeline.run_from_text(text)
                state.session.record(
                    SessionRecord(
                        input_text=text,
                        intent_action=result.action,
                        success=result.success,
                        message=result.message,
                        result_count=len(last_results),
                    )
                )

            elif msg_type == "execute":
                index = msg_data.get("index", 0)
                if 0 <= index < len(last_results):
                    target = last_results[index]
                    from gotit.domain.models import ActionType, Intent

                    intent = Intent(
                        action=ActionType.OPEN_FILE,
                        raw_text=f"open #{index}",
                    )
                    from gotit.adapters.executor.windows import WindowsExecutor

                    executor = WindowsExecutor()
                    result = await executor.execute(intent, [target])
                    await websocket.send_json(
                        {
                            "type": "executed",
                            "data": {
                                "success": result.success,
                                "action": result.action,
                                "message": result.message,
                            },
                        }
                    )
                else:
                    await websocket.send_json(
                        {"type": "error", "data": {"message": f"Invalid index: {index}"}}
                    )

            elif msg_type == "cancel":
                await websocket.send_json(
                    {"type": "state", "data": {"status": "cancelled"}}
                )

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            else:
                await websocket.send_json(
                    {"type": "error", "data": {"message": f"Unknown type: {msg_type}"}}
                )

    except WebSocketDisconnect:
        log.info("ws_disconnected")
    finally:
        for et in event_types:
            state.event_bus.unsubscribe(et, forward_event)
