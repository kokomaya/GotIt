"""Integration tests for Everything search adapter."""

from __future__ import annotations

import shutil

import pytest

from gotit.adapters.search.everything import EverythingAdapter, _build_query
from gotit.config import SearchConfig

ES_PATH = "D:\\03_Tools\\Everything\\es.exe"
es_available = shutil.which(ES_PATH) is not None or __import__("os").path.isfile(ES_PATH)


class TestBuildQuery:
    def test_simple_keyword(self):
        assert _build_query("readme", None) == "readme"

    def test_with_ext_filter(self):
        assert _build_query("*", {"ext": "pdf"}) == "ext:pdf"

    def test_with_multiple_filters(self):
        q = _build_query("report", {"ext": "docx", "dm": "thisweek"})
        assert "ext:docx" in q
        assert "dm:thisweek" in q
        assert "report" in q

    def test_with_path_filter(self):
        q = _build_query("*", {"path": "D:\\Projects"})
        assert 'path:"D:\\Projects"' in q

    def test_wildcard_alone(self):
        assert _build_query("*", None) == "*"

    def test_empty_query_no_filters(self):
        assert _build_query("", None) == "*"


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
