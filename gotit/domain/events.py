"""Domain events published during pipeline execution."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gotit.domain.models import ExecutionResult, Intent, SearchResult, Transcript


@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True, slots=True)
class TranscriptEvent(DomainEvent):
    transcript: Transcript | None = None
    partial: bool = False


@dataclass(frozen=True, slots=True)
class IntentEvent(DomainEvent):
    intent: Intent | None = None


@dataclass(frozen=True, slots=True)
class SearchEvent(DomainEvent):
    results: list[SearchResult] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ExecutionEvent(DomainEvent):
    result: ExecutionResult | None = None


@dataclass(frozen=True, slots=True)
class ErrorEvent(DomainEvent):
    stage: str = ""
    message: str = ""
