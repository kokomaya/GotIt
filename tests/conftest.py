"""Shared test fixtures: mock ports, test config, event bus."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from gotit.domain.models import (
    ActionType,
    ExecutionResult,
    Intent,
    SearchResult,
    Transcript,
)
from gotit.services.event_bus import EventBus

if TYPE_CHECKING:
    from datetime import datetime

    from gotit.domain.models import ActivityRecord, AudioChunk


class FakeSTT:
    async def transcribe(self, audio: AudioChunk) -> Transcript:
        return Transcript(text="打开记事本", language="zh", confidence=0.95)

    async def start_stream(self):
        yield Transcript(text="partial", language="zh")

    async def stop_stream(self) -> None:
        pass


class FakeLLM:
    async def parse_intent(
        self, text: str, context: list[str] | None = None
    ) -> Intent:
        return Intent(
            action=ActionType.RUN_PROGRAM,
            raw_text=text,
            target="notepad.exe",
        )


class FakeSearcher:
    async def search(
        self, query: str, filters: dict[str, str] | None = None
    ) -> list[SearchResult]:
        return [SearchResult(path="C:\\test.txt", filename="test.txt", size=100)]


class FakeExecutor:
    async def execute(
        self, intent: Intent, targets: list[SearchResult]
    ) -> ExecutionResult:
        return ExecutionResult(
            success=True,
            action=intent.action,
            message=f"Executed {intent.action.value}",
        )


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def fake_stt() -> FakeSTT:
    return FakeSTT()


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def fake_searcher() -> FakeSearcher:
    return FakeSearcher()


class FakeActivityStore:
    async def record_file_open(self, filepath: str, source: str = "recent") -> None:
        pass

    async def record_program_use(
        self, exe_path: str, window_title: str | None = None, source: str = "poll"
    ) -> None:
        pass

    async def search_files(
        self,
        query: str,
        time_range: tuple[datetime, datetime] | None = None,
        extensions: list[str] | None = None,
        limit: int = 20,
    ) -> list[ActivityRecord]:
        return []

    async def search_programs(
        self,
        query: str,
        time_range: tuple[datetime, datetime] | None = None,
        limit: int = 10,
    ) -> list[ActivityRecord]:
        return []

    async def cleanup(self, retention_days: int = 14) -> int:
        return 0


@pytest.fixture
def fake_executor() -> FakeExecutor:
    return FakeExecutor()


@pytest.fixture
def fake_activity_store() -> FakeActivityStore:
    return FakeActivityStore()
