"""Recent directory scanner — monitors Windows Recent folder for new .lnk files."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from gotit.config import ActivityConfig
    from gotit.domain.ports import ActivityStorePort

log = structlog.get_logger()

_RECENT_DIR = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Recent"


class RecentWatcher:
    def __init__(self, store: ActivityStorePort, config: ActivityConfig) -> None:
        self._store = store
        self._interval = config.recent_scan_interval
        self._excluded_ext = {e.lower() for e in config.excluded_extensions}
        self._last_scan_mtime: float = 0.0

    async def run(self) -> None:
        log.info("recent_watcher_started", dir=str(_RECENT_DIR))
        while True:
            try:
                await self._scan()
            except Exception:
                log.exception("recent_watcher_error")
            await asyncio.sleep(self._interval)

    async def _scan(self) -> None:
        if not _RECENT_DIR.is_dir():
            return

        new_cutoff = self._last_scan_mtime
        count = 0

        for entry in _RECENT_DIR.iterdir():
            if entry.suffix.lower() != ".lnk":
                continue
            try:
                mtime = entry.stat().st_mtime
            except OSError:
                continue
            if mtime <= self._last_scan_mtime:
                continue
            if mtime > new_cutoff:
                new_cutoff = mtime

            target = _parse_lnk(entry)
            if not target:
                continue

            ext = Path(target).suffix.lstrip(".").lower()
            if ext in self._excluded_ext:
                continue

            await self._store.record_file_open(target, source="recent")
            count += 1

        if count:
            log.debug("recent_watcher_scan", new_files=count)
        self._last_scan_mtime = new_cutoff


def _parse_lnk(lnk_path: Path) -> str | None:
    try:
        import pylnk3

        lnk = pylnk3.parse(str(lnk_path))
        path = lnk.path
        if path and Path(path).exists():
            return str(Path(path))
        if lnk.relative_path:
            resolved = (lnk_path.parent / lnk.relative_path).resolve()
            if resolved.exists():
                return str(resolved)
    except Exception:
        pass
    return None
