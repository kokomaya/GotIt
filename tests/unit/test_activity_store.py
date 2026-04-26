"""Tests for ActivityStore — SQLite CRUD, fuzzy search, time range, cleanup."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from gotit.services.activity_store import ActivityStore


@pytest.fixture
async def store(tmp_path):
    db_path = str(tmp_path / "test_activity.db")
    s = ActivityStore(db_path)
    yield s
    await s.close()


class TestRecordFileOpen:
    async def test_record_and_search(self, store):
        await store.record_file_open("C:\\docs\\report.xlsx")
        results = await store.search_files("report")
        assert len(results) == 1
        assert results[0].name == "report.xlsx"
        assert results[0].path == "C:\\docs\\report.xlsx"
        assert results[0].activity_type == "file"

    async def test_duplicate_ignored(self, store):
        await store.record_file_open("C:\\docs\\report.xlsx")
        await store.record_file_open("C:\\docs\\report.xlsx")
        results = await store.search_files("report")
        assert len(results) == 1

    async def test_extension_extracted(self, store):
        await store.record_file_open("C:\\data\\sheet.csv")
        results = await store.search_files("sheet", extensions=["csv"])
        assert len(results) == 1

    async def test_extension_filter_excludes(self, store):
        await store.record_file_open("C:\\data\\sheet.csv")
        results = await store.search_files("sheet", extensions=["pdf"])
        assert len(results) == 0


class TestRecordProgramUse:
    async def test_record_and_search(self, store):
        await store.record_program_use("C:\\Windows\\notepad.exe", window_title="Untitled")
        results = await store.search_programs("notepad")
        assert len(results) == 1
        assert results[0].name == "notepad.exe"
        assert results[0].window_title == "Untitled"

    async def test_search_by_window_title(self, store):
        await store.record_program_use(
            "C:\\Program Files\\Code\\code.exe", window_title="main.py - VS Code"
        )
        results = await store.search_programs("VS Code")
        assert len(results) == 1


class TestFuzzySearch:
    async def test_partial_filename(self, store):
        await store.record_file_open("C:\\work\\travel_request_0420.xlsx")
        results = await store.search_files("travel")
        assert len(results) == 1

    async def test_chinese_filename(self, store):
        await store.record_file_open("C:\\work\\出差申请表.xlsx")
        results = await store.search_files("申请")
        assert len(results) == 1

    async def test_no_match(self, store):
        await store.record_file_open("C:\\work\\report.pdf")
        results = await store.search_files("nonexistent")
        assert len(results) == 0


class TestTimeRange:
    async def test_within_range(self, store):
        await store.record_file_open("C:\\docs\\today.txt")
        now = datetime.now()
        results = await store.search_files(
            "today", time_range=(now - timedelta(hours=1), now + timedelta(hours=1))
        )
        assert len(results) == 1

    async def test_outside_range(self, store):
        await store.record_file_open("C:\\docs\\old.txt")
        future = datetime.now() + timedelta(days=30)
        results = await store.search_files(
            "old", time_range=(future, future + timedelta(days=1))
        )
        assert len(results) == 0


class TestCleanup:
    async def test_cleanup_old_records(self, store):
        await store.record_file_open("C:\\docs\\old.txt")
        # Manually backdating is complex, so just verify cleanup runs without error
        deleted = await store.cleanup(retention_days=14)
        assert deleted == 0  # just recorded, not old enough

    async def test_cleanup_returns_count(self, store):
        db = await store._get_db()
        old_date = (datetime.now() - timedelta(days=30)).isoformat()
        await db.execute(
            "INSERT INTO file_activity (filepath, filename, extension, opened_at) "
            "VALUES (?, ?, ?, ?)",
            ("C:\\old.txt", "old.txt", "txt", old_date),
        )
        await db.commit()
        deleted = await store.cleanup(retention_days=14)
        assert deleted == 1
