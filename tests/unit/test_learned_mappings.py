"""Tests for LearnedMappingStore — record, retrieve, prompt generation."""

from __future__ import annotations

from gotit.services.learned_mappings import LearnedMappingStore


class TestRecord:
    def test_record_and_retrieve(self, tmp_path):
        store = LearnedMappingStore(str(tmp_path / "mappings.yaml"))
        store.record("打开劳特巴赫", "D:\\tools\\lauterbach.cmd", "open_file")
        recent = store.get_recent()
        assert len(recent) == 1
        assert recent[0].input_text == "打开劳特巴赫"
        assert recent[0].resolved_path == "D:\\tools\\lauterbach.cmd"

    def test_duplicate_updates(self, tmp_path):
        store = LearnedMappingStore(str(tmp_path / "mappings.yaml"))
        store.record("打开劳特巴赫", "D:\\old\\path.cmd", "open_file")
        store.record("打开劳特巴赫", "D:\\new\\path.cmd", "open_file")
        recent = store.get_recent()
        assert len(recent) == 1
        assert recent[0].resolved_path == "D:\\new\\path.cmd"

    def test_case_insensitive_duplicate(self, tmp_path):
        store = LearnedMappingStore(str(tmp_path / "mappings.yaml"))
        store.record("打开Lauterbach", "D:\\a.cmd", "open_file")
        store.record("打开lauterbach", "D:\\b.cmd", "open_file")
        recent = store.get_recent()
        assert len(recent) == 1

    def test_multiple_entries(self, tmp_path):
        store = LearnedMappingStore(str(tmp_path / "mappings.yaml"))
        store.record("打开劳特巴赫", "D:\\a.cmd", "open_file")
        store.record("打开restbus", "D:\\b.bat", "open_file")
        recent = store.get_recent()
        assert len(recent) == 2
        assert recent[0].input_text == "打开restbus"


class TestPersistence:
    def test_save_and_reload(self, tmp_path):
        path = str(tmp_path / "mappings.yaml")
        store1 = LearnedMappingStore(path)
        store1.record("打开劳特巴赫", "D:\\tools\\t32.cmd", "open_file")

        store2 = LearnedMappingStore(path)
        recent = store2.get_recent()
        assert len(recent) == 1
        assert recent[0].input_text == "打开劳特巴赫"

    def test_empty_file(self, tmp_path):
        store = LearnedMappingStore(str(tmp_path / "nonexistent.yaml"))
        assert store.get_recent() == []


class TestPromptSection:
    def test_empty_returns_empty(self, tmp_path):
        store = LearnedMappingStore(str(tmp_path / "mappings.yaml"))
        assert store.to_prompt_section() == ""

    def test_generates_prompt(self, tmp_path):
        store = LearnedMappingStore(str(tmp_path / "mappings.yaml"))
        store.record("打开劳特巴赫", "D:\\tools\\Run_Lauterbach.cmd", "open_file")
        store.record("打开SW header", "D:\\docs\\SW_HeaderFormat.xlsx", "open_file")

        section = store.to_prompt_section()
        assert "打开劳特巴赫" in section
        assert "Run_Lauterbach.cmd" in section
        assert "SW_HeaderFormat.xlsx" in section
        assert "learned from this user" in section

    def test_limit(self, tmp_path):
        store = LearnedMappingStore(str(tmp_path / "mappings.yaml"))
        for i in range(20):
            store.record(f"command_{i}", f"D:\\file_{i}.txt", "open_file")

        section = store.to_prompt_section(limit=5)
        assert section.count("→") == 5
