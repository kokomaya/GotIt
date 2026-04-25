"""FastAPI dependency injection — provides shared app state to routes and websocket."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Request

if TYPE_CHECKING:
    from gotit.config import AppConfig
    from gotit.domain.pipeline import VoicePipeline
    from gotit.services.event_bus import EventBus
    from gotit.services.session import SessionManager


@dataclass
class _AppState:
    config: AppConfig
    pipeline: VoicePipeline
    event_bus: EventBus
    session: SessionManager


def _get_state(request: Request) -> _AppState:
    return request.app.state.app_state


AppState = Annotated[_AppState, Depends(_get_state)]
