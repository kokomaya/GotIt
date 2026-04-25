"""Tests for VoicePipeline: orchestration logic with mock ports."""

from __future__ import annotations

import pytest

from gotit.domain.events import (
    ErrorEvent,
    ExecutionEvent,
    IntentEvent,
    TranscriptEvent,
)
from gotit.domain.models import ActionType, AudioChunk, Intent
from gotit.domain.pipeline import VoicePipeline


@pytest.fixture
def pipeline(fake_stt, fake_llm, fake_searcher, fake_executor, event_bus):
    return VoicePipeline(
        stt=fake_stt,
        llm=fake_llm,
        searcher=fake_searcher,
        executor=fake_executor,
        event_bus=event_bus,
    )


class TestRunFromText:
    async def test_success(self, pipeline):
        result = await pipeline.run_from_text("打开记事本")
        assert result.success
        assert result.action == ActionType.RUN_PROGRAM

    async def test_publishes_events(self, pipeline, event_bus):
        events = []

        async def capture(event):
            events.append(event)

        event_bus.subscribe(TranscriptEvent, capture)
        event_bus.subscribe(IntentEvent, capture)
        event_bus.subscribe(ExecutionEvent, capture)

        await pipeline.run_from_text("打开记事本")

        event_types = [type(e) for e in events]
        assert TranscriptEvent in event_types
        assert IntentEvent in event_types
        assert ExecutionEvent in event_types


class TestRunOnce:
    async def test_success(self, pipeline):
        audio = AudioChunk(data=b"\x00" * 1600, sample_rate=16000, timestamp=0.0)
        result = await pipeline.run_once(audio)
        assert result.success


class TestPipelineErrorHandling:
    async def test_llm_failure(self, fake_stt, fake_searcher, fake_executor, event_bus):
        class FailingLLM:
            async def parse_intent(self, text, context=None):
                raise RuntimeError("LLM timeout")

        pipeline = VoicePipeline(
            stt=fake_stt,
            llm=FailingLLM(),
            searcher=fake_searcher,
            executor=fake_executor,
            event_bus=event_bus,
        )

        errors = []

        async def capture_error(event):
            errors.append(event)

        event_bus.subscribe(ErrorEvent, capture_error)

        result = await pipeline.run_from_text("test")
        assert not result.success
        assert "Intent parse failed" in result.message
        assert len(errors) == 1
        assert errors[0].stage == "intent"

    async def test_search_failure(self, fake_stt, fake_llm, fake_executor, event_bus):
        class SearchLLM:
            async def parse_intent(self, text, context=None):
                return Intent(action=ActionType.SEARCH, raw_text=text, query="*.py")

        class FailingSearcher:
            async def search(self, query, filters=None):
                raise ConnectionError("Everything not running")

        pipeline = VoicePipeline(
            stt=fake_stt,
            llm=SearchLLM(),
            searcher=FailingSearcher(),
            executor=fake_executor,
            event_bus=event_bus,
        )

        result = await pipeline.run_from_text("search py files")
        assert not result.success
        assert "Search failed" in result.message
