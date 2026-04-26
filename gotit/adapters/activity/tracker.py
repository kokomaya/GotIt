"""ActivityTracker — coordinates RecentWatcher + WindowPoller lifecycle."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog

from gotit.adapters.activity.recent_watcher import RecentWatcher
from gotit.adapters.activity.window_poller import WindowPoller

if TYPE_CHECKING:
    from gotit.config import ActivityConfig
    from gotit.domain.ports import ActivityStorePort

log = structlog.get_logger()


class ActivityTracker:
    def __init__(self, store: ActivityStorePort, config: ActivityConfig) -> None:
        self._store = store
        self._config = config
        self._watcher = RecentWatcher(store, config)
        self._poller = WindowPoller(store, config)
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        cleaned = await self._store.cleanup(self._config.retention_days)
        if cleaned:
            log.info("activity_startup_cleanup", deleted=cleaned)

        self._tasks = [
            asyncio.create_task(self._watcher.run(), name="recent-watcher"),
            asyncio.create_task(self._poller.run(), name="window-poller"),
            asyncio.create_task(self._periodic_cleanup(), name="activity-cleanup"),
        ]
        log.info("activity_tracker_started")

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()
        log.info("activity_tracker_stopped")

    async def _periodic_cleanup(self) -> None:
        while True:
            await asyncio.sleep(86400)
            try:
                await self._store.cleanup(self._config.retention_days)
            except Exception:
                log.exception("activity_periodic_cleanup_error")
