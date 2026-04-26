"""Tests for pipeline fuzzy resolution chain."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from gotit.domain.models import (
    ActionType,
    ActivityRecord,
    ExecutionResult,
    Intent,
    SearchResult,
)
from gotit.domain.pipeline import VoicePipeline, _time_ref_to_range
from gotit.services.event_bus import EventBus


class FakeSearcher:
    def __init__(self, results: list[SearchResult] | None = None):
        self._results = results or []
        self.calls: list[tuple[str, dict | None]] = []

    async def search(self, query: str, filters: dict | None = None) -> list[SearchResult]:
        self.calls.append((query, filters))
        return self._results


class FakeExecutor:
    async def execute(self, intent, targets):
        return ExecutionResult(success=True, action=intent.action, message="ok")


class FakeLLM:
    def __init__(self, intent: Intent):
        self._intent = intent

    async def parse_intent(self, text, context=None):
        return self._intent


class FakeSTT:
    async def transcribe(self, audio):
        raise NotImplementedError


class FakeActivityStore:
    def __init__(self, file_results=None, program_results=None):
        self._file_results = file_results or []
        self._program_results = program_results or []

    async def record_file_open(self, filepath, source="recent"):
        pass

    async def record_program_use(self, exe_path, window_title=None, source="poll"):
        pass

    async def search_files(self, query, time_range=None, extensions=None, limit=20):
        return self._file_results

    async def search_programs(self, query, time_range=None, limit=10):
        return self._program_results

    async def cleanup(self, retention_days=14):
        return 0


class TestFuzzyResolveFiles:
    async def test_strategy1_activity_history(self):
        """When activity history has results, use them directly."""
        activity_record = ActivityRecord(
            path="C:\\docs\\travel_request.xlsx",
            name="travel_request.xlsx",
            activity_type="file",
            last_opened=datetime.now(),
        )
        intent = Intent(
            action=ActionType.OPEN_FILE,
            raw_text="打开上周的出差申请表",
            query="出差申请表",
            match_mode="fuzzy",
            fuzzy_hints={
                "time_ref": "last_week",
                "description": "出差申请表",
                "synonyms": ["travel request"],
                "likely_ext": ["xlsx"],
            },
        )

        pipeline = VoicePipeline(
            stt=FakeSTT(),
            llm=FakeLLM(intent),
            searcher=FakeSearcher(),
            executor=FakeExecutor(),
            event_bus=EventBus(),
            activity_store=FakeActivityStore(file_results=[activity_record]),
        )

        result = await pipeline.run_from_text("打开上周的出差申请表")
        assert result.success

    async def test_strategy2_synonyms_fallback(self):
        """When activity history is empty, fall back to Everything + synonyms."""
        intent = Intent(
            action=ActionType.OPEN_FILE,
            raw_text="打开出差申请",
            query="出差申请",
            match_mode="fuzzy",
            fuzzy_hints={
                "synonyms": ["travel request"],
                "likely_ext": ["xlsx"],
            },
        )
        search_result = SearchResult(path="C:\\docs\\travel_request.xlsx", filename="travel_request.xlsx")

        searcher = FakeSearcher(results=[search_result])
        pipeline = VoicePipeline(
            stt=FakeSTT(),
            llm=FakeLLM(intent),
            searcher=searcher,
            executor=FakeExecutor(),
            event_bus=EventBus(),
            activity_store=FakeActivityStore(),
        )

        result = await pipeline.run_from_text("打开出差申请")
        assert result.success
        assert len(searcher.calls) > 0

    async def test_strategy3_relaxed_fallback(self):
        """When synonyms fail, try relaxed search with partial_name."""
        intent = Intent(
            action=ActionType.OPEN_FILE,
            raw_text="那个auto什么的配置",
            query="auto",
            match_mode="fuzzy",
            fuzzy_hints={
                "partial_name": "auto",
                "description": "配置文件",
                "synonyms": [],
            },
        )

        call_count = 0
        results_by_call: list[list[SearchResult]] = [
            [],  # synonym search (query "auto") returns nothing
            [SearchResult(path="C:\\config\\autosar.xml", filename="autosar.xml")],  # relaxed *auto*
        ]

        class TrackingSearcher:
            async def search(self, query, filters=None):
                nonlocal call_count
                idx = min(call_count, len(results_by_call) - 1)
                result = results_by_call[idx]
                call_count += 1
                return result

        pipeline = VoicePipeline(
            stt=FakeSTT(),
            llm=FakeLLM(intent),
            searcher=TrackingSearcher(),
            executor=FakeExecutor(),
            event_bus=EventBus(),
            activity_store=FakeActivityStore(),
        )

        result = await pipeline.run_from_text("那个auto什么的配置")
        assert result.success

    async def test_exact_mode_skips_fuzzy(self):
        """Exact mode goes straight to Everything search."""
        intent = Intent(
            action=ActionType.SEARCH,
            raw_text="搜索 *.py",
            query="*.py",
            match_mode="exact",
        )
        search_result = SearchResult(path="C:\\code\\main.py", filename="main.py")

        searcher = FakeSearcher(results=[search_result])
        pipeline = VoicePipeline(
            stt=FakeSTT(),
            llm=FakeLLM(intent),
            searcher=searcher,
            executor=FakeExecutor(),
            event_bus=EventBus(),
            activity_store=FakeActivityStore(),
        )

        result = await pipeline.run_from_text("搜索 *.py")
        assert result.success
        assert len(searcher.calls) == 1
        assert searcher.calls[0][0] == "*.py"


class TestFuzzyResolveProgram:
    async def test_alias_resolution(self):
        """Fuzzy program resolve uses alias table."""
        intent = Intent(
            action=ActionType.RUN_PROGRAM,
            raw_text="打开画图",
            target="画图",
            match_mode="fuzzy",
            fuzzy_hints={"synonyms": ["mspaint", "paint"]},
        )

        program_record = ActivityRecord(
            path="C:\\Windows\\System32\\mspaint.exe",
            name="mspaint.exe",
            activity_type="program",
            last_opened=datetime.now(),
        )

        pipeline = VoicePipeline(
            stt=FakeSTT(),
            llm=FakeLLM(intent),
            searcher=FakeSearcher(),
            executor=FakeExecutor(),
            event_bus=EventBus(),
            activity_store=FakeActivityStore(program_results=[program_record]),
        )

        result = await pipeline.run_from_text("打开画图")
        assert result.success


class TestTimeRefToRange:
    def test_today(self):
        result = _time_ref_to_range("today")
        assert result is not None
        start, end = result
        assert start.hour == 0
        assert end <= datetime.now()

    def test_last_week(self):
        result = _time_ref_to_range("last_week")
        assert result is not None
        start, end = result
        assert (end - start).days == 7

    def test_recent(self):
        result = _time_ref_to_range("recent")
        assert result is not None
        start, end = result
        assert (end - start).total_seconds() <= 7200 + 1

    def test_none(self):
        assert _time_ref_to_range(None) is None

    def test_unknown(self):
        assert _time_ref_to_range("unknown_value") is None
