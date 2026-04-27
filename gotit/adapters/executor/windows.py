"""Windows shell executor for ExecutorPort — open files, folders, programs."""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from gotit.domain.models import ActionType, ExecutionResult, Intent, SearchResult

if TYPE_CHECKING:
    from gotit.config import SearchConfig

log = structlog.get_logger()

_BLOCKED_EXTENSIONS = {".ps1", ".vbs", ".js", ".wsf", ".msi"}


class WindowsExecutor:
    def __init__(self, search_config: SearchConfig | None = None) -> None:
        self._es_path = search_config.everything_path if search_config else "es.exe"

    async def execute(
        self, intent: Intent, targets: list[SearchResult]
    ) -> ExecutionResult:
        if intent.action == ActionType.RUN_PROGRAM:
            return await self._handle_run_program(intent, targets)
        if intent.action == ActionType.OPEN_FILE:
            return await self._handle_open_file(intent, targets)
        if intent.action == ActionType.OPEN_FOLDER:
            return await self._handle_open_folder(intent, targets)
        handler = _HANDLERS.get(intent.action)
        if handler is None:
            return ExecutionResult(
                success=False,
                action=intent.action,
                message=f"Unsupported action: {intent.action}",
            )
        return handler(intent, targets)

    async def _handle_run_program(
        self, intent: Intent, targets: list[SearchResult]
    ) -> ExecutionResult:
        program = intent.target
        if not program and not targets:
            return ExecutionResult(
                success=False,
                action=ActionType.RUN_PROGRAM,
                message="No program specified",
            )

        if len(targets) > 1:
            summary = "\n".join(
                f"  [{i + 1}] {r.filename}  ({r.path})" for i, r in enumerate(targets[:10])
            )
            return ExecutionResult(
                success=True,
                action=ActionType.RUN_PROGRAM,
                message=f"Found {len(targets)} matches:\n{summary}",
                data={"count": len(targets), "pending_selection": True},
            )

        resolved = None
        _RUNNABLE_EXT = {".exe", ".bat", ".cmd"}
        if targets:
            candidate = Path(targets[0].path)
            if candidate.suffix.lower() in _RUNNABLE_EXT and candidate.is_file():
                resolved = str(candidate)

        if not resolved and program:
            log.info("resolving_program", program=program)
            resolved = shutil.which(program)
            if not resolved:
                resolved = await self._resolve_via_everything(program)

        if not resolved:
            return ExecutionResult(
                success=False,
                action=ActionType.RUN_PROGRAM,
                message=f"Program not found: {program or '(unknown)'}",
            )

        log.debug("running_program", program=resolved)
        subprocess.Popen([resolved], shell=False)
        return ExecutionResult(
            success=True,
            action=ActionType.RUN_PROGRAM,
            message=f"Launched {program}",
        )

    async def _handle_open_file(
        self, intent: Intent, targets: list[SearchResult]
    ) -> ExecutionResult:
        if not targets:
            return ExecutionResult(
                success=False, action=ActionType.OPEN_FILE, message="No file found to open"
            )

        if len(targets) > 1:
            summary = "\n".join(
                f"  [{i + 1}] {r.filename}  ({r.path})" for i, r in enumerate(targets[:10])
            )
            return ExecutionResult(
                success=True,
                action=ActionType.OPEN_FILE,
                message=f"Found {len(targets)} matches:\n{summary}",
                data={"count": len(targets), "pending_selection": True},
            )

        target = targets[0]
        if not _validate_path(target.path):
            return ExecutionResult(
                success=False,
                action=ActionType.OPEN_FILE,
                message=f"Blocked: {target.filename}",
            )

        if intent.with_program:
            return await self._open_with_program(
                intent.with_program, target.path, ActionType.OPEN_FILE
            )

        log.info("opening_file", path=target.path)
        os.startfile(target.path)
        return ExecutionResult(
            success=True, action=ActionType.OPEN_FILE, message=f"Opened {target.filename}"
        )

    async def _handle_open_folder(
        self, intent: Intent, targets: list[SearchResult]
    ) -> ExecutionResult:
        folder = intent.target
        if not folder and targets:
            p = Path(targets[0].path)
            folder = str(p) if p.is_dir() else str(p.parent)

        if not folder:
            return ExecutionResult(
                success=False, action=ActionType.OPEN_FOLDER, message="No folder specified"
            )

        if not Path(folder).is_dir():
            return ExecutionResult(
                success=False,
                action=ActionType.OPEN_FOLDER,
                message=f"Not a folder: {folder}",
            )

        if intent.with_program:
            return await self._open_with_program(
                intent.with_program, folder, ActionType.OPEN_FOLDER
            )

        log.info("opening_folder", path=folder)
        subprocess.Popen(["explorer.exe", folder])
        return ExecutionResult(
            success=True, action=ActionType.OPEN_FOLDER, message=f"Opened {folder}"
        )

    async def _open_with_program(
        self, program: str, target_path: str, action: ActionType
    ) -> ExecutionResult:
        resolved = shutil.which(program)
        if not resolved:
            resolved = await self._resolve_via_everything(program)
        if not resolved:
            return ExecutionResult(
                success=False,
                action=action,
                message=f"Program not found: {program}",
            )

        log.info("opening_with_program", program=resolved, target=target_path)
        subprocess.Popen([resolved, target_path], shell=False)
        return ExecutionResult(
            success=True,
            action=action,
            message=f"Opened {Path(target_path).name} with {Path(resolved).stem}",
        )

    async def _resolve_via_everything(self, program: str) -> str | None:
        exe_name = program if program.lower().endswith(".exe") else f"{program}.exe"
        cmd = [self._es_path, exe_name, "-n", "10"]
        log.debug("everything_program_search", query=exe_name)
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        except (FileNotFoundError, TimeoutError):
            log.warning("everything_resolve_unavailable")
            return None

        if proc.returncode != 0:
            return None

        lines = stdout.decode("utf-8", errors="replace").strip().splitlines()
        for line in lines:
            path = line.strip()
            if not path:
                continue
            p = Path(path)
            if p.suffix.lower() == ".exe" and p.is_file():
                log.info("everything_resolved", program=program, path=path)
                return path

        return None


def _handle_search(intent: Intent, targets: list[SearchResult]) -> ExecutionResult:
    if not targets:
        return ExecutionResult(
            success=True, action=ActionType.SEARCH, message="No results found"
        )
    summary = "\n".join(f"  {r.filename}  ({r.path})" for r in targets[:10])
    return ExecutionResult(
        success=True,
        action=ActionType.SEARCH,
        message=f"Found {len(targets)} results:\n{summary}",
        data={"count": len(targets)},
    )


def _handle_system_control(
    intent: Intent, targets: list[SearchResult]
) -> ExecutionResult:
    return ExecutionResult(
        success=False,
        action=ActionType.SYSTEM_CONTROL,
        message="System control not yet implemented",
    )


def _validate_path(filepath: str) -> bool:
    ext = Path(filepath).suffix.lower()
    if ext in _BLOCKED_EXTENSIONS:
        log.warning("blocked_extension", path=filepath, ext=ext)
        return False
    try:
        resolved = Path(filepath).resolve()
        if ".." in resolved.parts:
            return False
    except (OSError, ValueError):
        return False
    return True


_HANDLERS = {
    ActionType.SEARCH: _handle_search,
    ActionType.SYSTEM_CONTROL: _handle_system_control,
}
