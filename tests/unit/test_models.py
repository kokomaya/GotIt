"""Tests for domain models: creation, immutability, serialization."""

from __future__ import annotations

import pytest

from gotit.domain.models import (
    ActionType,
    AudioChunk,
    AudioDevice,
    ExecutionResult,
    Intent,
    SearchResult,
    Transcript,
)


class TestAudioChunk:
    def test_create(self):
        chunk = AudioChunk(data=b"\x00\x01", sample_rate=16000, timestamp=1.0)
        assert chunk.data == b"\x00\x01"
        assert chunk.sample_rate == 16000

    def test_frozen(self):
        chunk = AudioChunk(data=b"", sample_rate=16000, timestamp=0.0)
        with pytest.raises(AttributeError):
            chunk.data = b"new"  # type: ignore[misc]


class TestTranscript:
    def test_defaults(self):
        t = Transcript(text="hello")
        assert t.language == "zh"
        assert t.confidence == 1.0

    def test_custom(self):
        t = Transcript(text="hello", language="en", confidence=0.8)
        assert t.language == "en"


class TestActionType:
    def test_values(self):
        assert ActionType.SEARCH == "search"
        assert ActionType.OPEN_FILE == "open_file"
        assert ActionType.RUN_PROGRAM == "run_program"

    def test_is_str(self):
        assert isinstance(ActionType.SEARCH, str)


class TestIntent:
    def test_minimal(self):
        intent = Intent(action=ActionType.SEARCH, raw_text="find files")
        assert intent.query is None
        assert intent.filters == {}
        assert intent.confidence == 1.0

    def test_full(self):
        intent = Intent(
            action=ActionType.OPEN_FILE,
            raw_text="open design doc",
            query="design",
            target="D:\\docs",
            filters={"ext": "pdf"},
            confidence=0.9,
        )
        assert intent.filters["ext"] == "pdf"


class TestSearchResult:
    def test_defaults(self):
        sr = SearchResult(path="C:\\a.txt", filename="a.txt")
        assert sr.size == 0
        assert sr.modified is None
        assert sr.match_score == 0.0


class TestExecutionResult:
    def test_success(self):
        er = ExecutionResult(success=True, action=ActionType.SEARCH, message="ok")
        assert er.data is None

    def test_failure(self):
        er = ExecutionResult(
            success=False,
            action=ActionType.RUN_PROGRAM,
            message="not found",
            data={"code": 404},
        )
        assert not er.success
        assert er.data["code"] == 404


class TestAudioDevice:
    def test_create(self):
        dev = AudioDevice(index=0, name="Microphone")
        assert not dev.is_default
