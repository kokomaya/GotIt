"""Tests for intent parsing — ClaudeAdapter response parsing logic."""

from __future__ import annotations

from gotit.adapters.llm.claude import _parse_response
from gotit.domain.models import ActionType


class TestParseResponse:
    def test_open_file_with_date(self):
        raw = '{"action":"open_file","query":"设计文档","target":null,"filters":{"dm":"yesterday"},"confidence":0.9}'
        intent = _parse_response(raw, "打开昨天的设计文档")
        assert intent.action == ActionType.OPEN_FILE
        assert intent.query == "设计文档"
        assert intent.filters["dm"] == "yesterday"
        assert intent.raw_text == "打开昨天的设计文档"

    def test_search_pdf(self):
        raw = '{"action":"search","query":"*","target":null,"filters":{"ext":"pdf"},"confidence":0.95}'
        intent = _parse_response(raw, "搜索所有PDF文件")
        assert intent.action == ActionType.SEARCH
        assert intent.filters["ext"] == "pdf"

    def test_run_program(self):
        raw = '{"action":"run_program","query":null,"target":"code","filters":{},"confidence":0.95}'
        intent = _parse_response(raw, "打开Visual Studio Code")
        assert intent.action == ActionType.RUN_PROGRAM
        assert intent.target == "code"
        assert intent.query is None

    def test_open_folder(self):
        raw = '{"action":"open_folder","query":null,"target":"D:\\\\Projects","filters":{},"confidence":0.9}'
        intent = _parse_response(raw, "打开D盘的项目文件夹")
        assert intent.action == ActionType.OPEN_FOLDER
        assert intent.target == "D:\\Projects"

    def test_markdown_fenced_json(self):
        raw = '```json\n{"action":"search","query":"report","target":null,"filters":{},"confidence":0.8}\n```'
        intent = _parse_response(raw, "find report")
        assert intent.action == ActionType.SEARCH
        assert intent.query == "report"

    def test_invalid_json_fallback(self):
        raw = "I don't understand your request"
        intent = _parse_response(raw, "some gibberish")
        assert intent.action == ActionType.SEARCH
        assert intent.query == "some gibberish"
        assert intent.confidence == 0.3

    def test_unknown_action_fallback(self):
        raw = '{"action":"fly_to_moon","query":"moon","filters":{}}'
        intent = _parse_response(raw, "fly to moon")
        assert intent.action == ActionType.SEARCH

    def test_empty_filters_stripped(self):
        raw = '{"action":"search","query":"test","target":null,"filters":{"ext":"","path":"D:\\\\Work"},"confidence":0.9}'
        intent = _parse_response(raw, "test")
        assert "ext" not in intent.filters
        assert intent.filters["path"] == "D:\\Work"
