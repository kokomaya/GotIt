"""Domain models: AudioChunk, Transcript, Intent, SearchResult, ExecutionResult."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime


class ActionType(StrEnum):
    SEARCH = "search"
    OPEN_FILE = "open_file"
    OPEN_FOLDER = "open_folder"
    RUN_PROGRAM = "run_program"
    SYSTEM_CONTROL = "system_control"


@dataclass(frozen=True, slots=True)
class AudioChunk:
    data: bytes
    sample_rate: int
    timestamp: float


@dataclass(frozen=True, slots=True)
class Transcript:
    text: str
    language: str = "zh"
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class Intent:
    action: ActionType
    raw_text: str
    query: str | None = None
    target: str | None = None
    filters: dict[str, str] = field(default_factory=dict)
    confidence: float = 1.0
    match_mode: str = "exact"
    fuzzy_hints: dict[str, Any] | None = None
    with_program: str | None = None


@dataclass(frozen=True, slots=True)
class AudioDevice:
    index: int
    name: str
    is_default: bool = False


@dataclass(frozen=True, slots=True)
class SearchResult:
    path: str
    filename: str
    size: int = 0
    modified: datetime | None = None
    match_score: float = 0.0


@dataclass(frozen=True, slots=True)
class ActivityRecord:
    path: str
    name: str
    activity_type: str
    last_opened: datetime
    open_count: int = 1
    window_title: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    success: bool
    action: ActionType
    message: str
    data: dict | None = None
