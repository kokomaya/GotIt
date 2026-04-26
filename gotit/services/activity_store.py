"""SQLite-backed activity store — records and queries file/program usage history."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import aiosqlite
import structlog

from gotit.domain.models import ActivityRecord

if TYPE_CHECKING:
    pass

log = structlog.get_logger()

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS file_activity (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath    TEXT NOT NULL,
    filename    TEXT NOT NULL,
    extension   TEXT,
    opened_at   TIMESTAMP NOT NULL,
    source      TEXT DEFAULT 'recent',
    UNIQUE(filepath, opened_at)
);
CREATE INDEX IF NOT EXISTS idx_file_filename ON file_activity(filename);
CREATE INDEX IF NOT EXISTS idx_file_opened_at ON file_activity(opened_at);

CREATE TABLE IF NOT EXISTS program_activity (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    exe_path    TEXT NOT NULL,
    exe_name    TEXT NOT NULL,
    window_title TEXT,
    started_at  TIMESTAMP NOT NULL,
    last_seen   TIMESTAMP NOT NULL,
    source      TEXT DEFAULT 'poll',
    UNIQUE(exe_path, started_at)
);
CREATE INDEX IF NOT EXISTS idx_prog_exe_name ON program_activity(exe_name);
CREATE INDEX IF NOT EXISTS idx_prog_last_seen ON program_activity(last_seen);
"""


class ActivityStore:
    def __init__(self, db_path: str) -> None:
        resolved = Path(db_path).expanduser()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(resolved)
        self._db: aiosqlite.Connection | None = None

    async def _get_db(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(self._db_path)
            self._db.row_factory = aiosqlite.Row
            await self._db.executescript(_SCHEMA)
            await self._db.commit()
        return self._db

    async def record_file_open(self, filepath: str, source: str = "recent") -> None:
        db = await self._get_db()
        p = Path(filepath)
        now = datetime.now().isoformat()
        ext = p.suffix.lstrip(".").lower() if p.suffix else None
        await db.execute(
            "INSERT OR IGNORE INTO file_activity (filepath, filename, extension, opened_at, source) "
            "VALUES (?, ?, ?, ?, ?)",
            (str(p), p.name, ext, now, source),
        )
        await db.commit()

    async def record_program_use(
        self, exe_path: str, window_title: str | None = None, source: str = "poll"
    ) -> None:
        db = await self._get_db()
        exe_name = Path(exe_path).name
        now = datetime.now().isoformat()
        try:
            await db.execute(
                "INSERT INTO program_activity (exe_path, exe_name, window_title, started_at, last_seen, source) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (exe_path, exe_name, window_title, now, now, source),
            )
        except aiosqlite.IntegrityError:
            await db.execute(
                "UPDATE program_activity SET last_seen = ?, window_title = ? "
                "WHERE exe_path = ? AND started_at = ("
                "  SELECT MAX(started_at) FROM program_activity WHERE exe_path = ?"
                ")",
                (now, window_title, exe_path, exe_path),
            )
        await db.commit()

    async def search_files(
        self,
        query: str,
        time_range: tuple[datetime, datetime] | None = None,
        extensions: list[str] | None = None,
        limit: int = 20,
    ) -> list[ActivityRecord]:
        db = await self._get_db()
        conditions = ["filename LIKE ?"]
        params: list[object] = [f"%{query}%"]

        if time_range:
            conditions.append("opened_at BETWEEN ? AND ?")
            params.extend([time_range[0].isoformat(), time_range[1].isoformat()])

        if extensions:
            placeholders = ",".join("?" for _ in extensions)
            conditions.append(f"extension IN ({placeholders})")
            params.extend(e.lower() for e in extensions)

        where = " AND ".join(conditions)
        sql = (
            f"SELECT filepath, filename, MAX(opened_at) as last_opened, COUNT(*) as cnt "
            f"FROM file_activity WHERE {where} "
            f"GROUP BY filepath "
            f"ORDER BY last_opened DESC, cnt DESC "
            f"LIMIT ?"
        )
        params.append(limit)

        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        return [
            ActivityRecord(
                path=row["filepath"],
                name=row["filename"],
                activity_type="file",
                last_opened=datetime.fromisoformat(row["last_opened"]),
                open_count=row["cnt"],
            )
            for row in rows
        ]

    async def search_programs(
        self,
        query: str,
        time_range: tuple[datetime, datetime] | None = None,
        limit: int = 10,
    ) -> list[ActivityRecord]:
        db = await self._get_db()
        conditions = ["(exe_name LIKE ? OR window_title LIKE ?)"]
        params: list[object] = [f"%{query}%", f"%{query}%"]

        if time_range:
            conditions.append("last_seen BETWEEN ? AND ?")
            params.extend([time_range[0].isoformat(), time_range[1].isoformat()])

        where = " AND ".join(conditions)
        sql = (
            f"SELECT exe_path, exe_name, window_title, MAX(last_seen) as last_seen "
            f"FROM program_activity WHERE {where} "
            f"GROUP BY exe_path "
            f"ORDER BY last_seen DESC "
            f"LIMIT ?"
        )
        params.append(limit)

        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        return [
            ActivityRecord(
                path=row["exe_path"],
                name=row["exe_name"],
                activity_type="program",
                last_opened=datetime.fromisoformat(row["last_seen"]),
                window_title=row["window_title"],
            )
            for row in rows
        ]

    async def cleanup(self, retention_days: int = 14) -> int:
        db = await self._get_db()
        from datetime import timedelta

        cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()
        cursor1 = await db.execute("DELETE FROM file_activity WHERE opened_at < ?", (cutoff,))
        cursor2 = await db.execute("DELETE FROM program_activity WHERE last_seen < ?", (cutoff,))
        await db.commit()
        total = (cursor1.rowcount or 0) + (cursor2.rowcount or 0)
        if total:
            log.info("activity_cleanup", deleted=total, retention_days=retention_days)
        return total

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None
