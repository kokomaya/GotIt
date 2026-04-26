"""Tests for program alias resolution."""

from __future__ import annotations

from gotit.adapters.activity.aliases import resolve_aliases


class TestResolveAliases:
    def test_chinese_name(self):
        result = resolve_aliases("画图")
        assert "mspaint.exe" in result

    def test_english_name(self):
        result = resolve_aliases("notepad")
        assert "notepad.exe" in result

    def test_abbreviation(self):
        result = resolve_aliases("PS")
        assert "photoshop.exe" in result

    def test_case_insensitive(self):
        result = resolve_aliases("CHROME")
        assert "chrome.exe" in result

    def test_unknown_returns_empty(self):
        result = resolve_aliases("some_unknown_program_xyz")
        assert result == []

    def test_vscode(self):
        result = resolve_aliases("vscode")
        assert "code.exe" in result

    def test_office_word(self):
        result = resolve_aliases("word")
        assert "winword.exe" in result
