"""Tests for _parse_response with match_mode and fuzzy_hints."""

from __future__ import annotations

from gotit.adapters.llm.claude import _parse_response
from gotit.domain.models import ActionType


class TestMatchMode:
    def test_exact_mode_default(self):
        raw = '{"action":"search","query":"*.py","filters":{},"confidence":0.9}'
        intent = _parse_response(raw, "搜索py文件")
        assert intent.match_mode == "exact"
        assert intent.fuzzy_hints is None

    def test_explicit_exact(self):
        raw = '{"action":"run_program","target":"notepad","filters":{},"match_mode":"exact","confidence":0.95}'
        intent = _parse_response(raw, "打开记事本")
        assert intent.match_mode == "exact"
        assert intent.fuzzy_hints is None

    def test_fuzzy_mode(self):
        raw = (
            '{"action":"open_file","query":"出差申请表","filters":{},'
            '"match_mode":"fuzzy",'
            '"fuzzy_hints":{"time_ref":"last_week","partial_name":null,'
            '"description":"出差申请表","synonyms":["travel request"],'
            '"likely_ext":["xlsx","docx"]},'
            '"confidence":0.85}'
        )
        intent = _parse_response(raw, "打开上周的出差申请表")
        assert intent.match_mode == "fuzzy"
        assert intent.fuzzy_hints is not None
        assert intent.fuzzy_hints["time_ref"] == "last_week"
        assert "travel request" in intent.fuzzy_hints["synonyms"]
        assert "xlsx" in intent.fuzzy_hints["likely_ext"]

    def test_fuzzy_program(self):
        raw = (
            '{"action":"run_program","target":"画图","filters":{},'
            '"match_mode":"fuzzy",'
            '"fuzzy_hints":{"synonyms":["mspaint","paint"]},'
            '"confidence":0.9}'
        )
        intent = _parse_response(raw, "打开画图")
        assert intent.action == ActionType.RUN_PROGRAM
        assert intent.match_mode == "fuzzy"
        assert "mspaint" in intent.fuzzy_hints["synonyms"]

    def test_missing_match_mode_defaults_exact(self):
        raw = '{"action":"search","query":"test","filters":{},"confidence":0.8}'
        intent = _parse_response(raw, "test")
        assert intent.match_mode == "exact"

    def test_invalid_json_fallback_is_exact(self):
        intent = _parse_response("not json at all", "test")
        assert intent.match_mode == "exact"
        assert intent.action == ActionType.SEARCH
