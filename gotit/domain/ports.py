"""Port interfaces (abstractions) for infrastructure adapters.

Each port defines a single responsibility (ISP).
Pipeline depends only on these abstractions, never on concrete adapters (DIP).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from gotit.domain.models import (
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
