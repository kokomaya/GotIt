"""Integration tests for Everything search adapter."""

from __future__ import annotations

import shutil

import pytest

from gotit.adapters.search.everything import EverythingAdapter, _build_query_args
from gotit.config import SearchConfig

ES_PATH = "D:\\03_Tools\\Everything\\es.exe"
es_available = shutil.which(ES_PATH) is not None or __import__("os").path.isfile(ES_PATH)


class TestBuildQuery:
    def test_simple_keyword(self):
        assert _build_query_args("readme", None) == ["readme"]

    def test_with_ext_filter(self):
        assert _build_query_args("*", {"ext": "pdf"}) == ["ext:pdf"]

    def test_with_multiple_filters(self):
        parts = _build_query_args("report", {"ext": "docx", "dm": "thisweek"})
        assert "ext:docx" in parts
        assert "dm:thisweek" in parts
        assert "report" in parts

    def test_with_path_filter(self):
        parts = _build_query_args("*", {"path": "D:\\Projects"})
        assert 'path:"D:\\Projects"' in parts

    def test_wildcard_alone(self):
        assert _build_query_args("*", None) == ["*"]

    def test_empty_query_no_filters(self):
        assert _build_query_args("", None) == ["*"]

    def test_wildcard_query_separate_from_filter(self):
        parts = _build_query_args("*SW*Header*", {"ext": "xlsx"})
        assert parts == ["ext:xlsx", "*SW*Header*"]

    def test_order_independent_wildcards_split(self):
        parts = _build_query_args("*IPC* *concept*", {"ext": "docx"})
        assert parts == ["ext:docx", "*IPC*", "*concept*"]


@pytest.mark.skipif(not es_available, reason="es.exe not found")
class TestEverythingAdapterIntegration:
    @pytest.fixture
    def adapter(self):
        return EverythingAdapter(SearchConfig(everything_path=ES_PATH, max_results=5))

    async def test_search_known_file(self, adapter):
        results = await adapter.search("pyproject.toml")
        assert len(results) > 0
        assert any("pyproject.toml" in r.filename for r in results)

    async def test_search_with_ext_filter(self, adapter):
        results = await adapter.search("*", {"ext": "py"})
        assert len(results) > 0
        assert all(r.filename.endswith(".py") for r in results)

    async def test_search_nonexistent(self, adapter):
        results = await adapter.search("zzz_nonexistent_file_12345.xyz")
        assert len(results) == 0

    async def test_result_has_metadata(self, adapter):
        results = await adapter.search("pyproject.toml")
        assert len(results) > 0
        r = results[0]
        assert r.size > 0
        assert r.modified is not None
