"""Foreground window poller — samples the active window to track program usage."""

from __future__ import annotations

import asyncio
import ctypes
import ctypes.wintypes
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from gotit.config import ActivityConfig
    from gotit.domain.ports import ActivityStorePort

log = structlog.get_logger()

_user32 = ctypes.windll.user32  # type: ignore[attr-defined]
_kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
_psapi = ctypes.windll.psapi  # type: ignore[attr-defined]

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010


class WindowPoller:
    def __init__(self, store: ActivityStorePort, config: ActivityConfig) -> None:
        self._store = store
        self._interval = config.window_poll_interval
        self._excluded = {e.lower() for e in config.excluded_programs}
        self._last_exe: str | None = None

    async def run(self) -> None:
        log.info("window_poller_started", interval=self._interval)
        while True:
            try:
                await self._poll()
            except Exception:
                log.exception("window_poller_error")
            await asyncio.sleep(self._interval)

    async def _poll(self) -> None:
        info = _get_foreground_info()
        if not info:
            return

        exe_path, window_title = info
        exe_name = Path(exe_path).name.lower()

        if exe_name in self._excluded:
            return

        if exe_path == self._last_exe:
            await self._store.record_program_use(
                exe_path, window_title=window_title, source="poll"
            )
            return

        self._last_exe = exe_path
        await self._store.record_program_use(
            exe_path, window_title=window_title, source="poll"
        )
        log.debug("window_poller_new", exe=exe_name, title=window_title)


def _get_foreground_info() -> tuple[str, str] | None:
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return None

    title_buf = ctypes.create_unicode_buffer(512)
    _user32.GetWindowTextW(hwnd, title_buf, 512)
    window_title = title_buf.value

    pid = ctypes.wintypes.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return None

    handle = _kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid.value)
    if not handle:
        return None

    try:
        exe_buf = ctypes.create_unicode_buffer(1024)
        result = _psapi.GetModuleFileNameExW(handle, None, exe_buf, 1024)
        if not result:
            return None
        return exe_buf.value, window_title
    finally:
        _kernel32.CloseHandle(handle)
