"""Port interfaces (abstractions) for infrastructure adapters.

Each port defines a single responsibility (ISP).
Pipeline depends only on these abstractions, never on concrete adapters (DIP).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from datetime import datetime

    from gotit.domain.models import (
        ActivityRecord,
        AudioChunk,
        AudioDevice,
        ExecutionResult,
        Intent,
        SearchResult,
        Transcript,
    )


class AudioCapturePort(Protocol):
    async def start(self) -> AsyncIterator[AudioChunk]: ...
    async def stop(self) -> None: ...
    def list_devices(self) -> list[AudioDevice]: ...


class STTPort(Protocol):
    async def transcribe(self, audio: AudioChunk) -> Transcript: ...
    async def start_stream(self) -> AsyncIterator[Transcript]: ...
    async def stop_stream(self) -> None: ...


class LLMPort(Protocol):
    async def parse_intent(
        self, text: str, context: list[str] | None = None
    ) -> Intent: ...


class SearchPort(Protocol):
    async def search(
        self, query: str, filters: dict[str, str] | None = None
    ) -> list[SearchResult]: ...


class ExecutorPort(Protocol):
    async def execute(
        self, intent: Intent, targets: list[SearchResult]
    ) -> ExecutionResult: ...


class ActivityStorePort(Protocol):
    async def record_file_open(
        self, filepath: str, source: str = "recent"
    ) -> None: ...

    async def record_program_use(
        self, exe_path: str, window_title: str | None = None,
        source: str = "poll",
    ) -> None: ...

    async def search_files(
        self, query: str,
        time_range: tuple[datetime, datetime] | None = None,
        extensions: list[str] | None = None,
        limit: int = 20,
    ) -> list[ActivityRecord]: ...

    async def search_programs(
        self, query: str,
        time_range: tuple[datetime, datetime] | None = None,
        limit: int = 10,
    ) -> list[ActivityRecord]: ...

    async def cleanup(self, retention_days: int = 14) -> int: ...
