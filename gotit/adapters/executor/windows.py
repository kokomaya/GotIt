"""Windows shell executor for ExecutorPort — open files, folders, programs."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import structlog

from gotit.domain.models import ActionType, ExecutionResult, Intent, SearchResult

log = structlog.get_logger()

_BLOCKED_EXTENSIONS = {".bat", ".cmd", ".ps1", ".vbs", ".js", ".wsf", ".msi"}


class WindowsExecutor:
    async def execute(
        self, intent: Intent, targets: list[SearchResult]
    ) -> ExecutionResult:
        handler = _HANDLERS.get(intent.action)
        if handler is None:
            return ExecutionResult(
                success=False,
                action=intent.action,
                message=f"Unsupported action: {intent.action}",
            )
        return handler(intent, targets)


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


def _handle_open_file(intent: Intent, targets: list[SearchResult]) -> ExecutionResult:
    if not targets:
        return ExecutionResult(
            success=False, action=ActionType.OPEN_FILE, message="No file found to open"
        )

    target = targets[0]
    if not _validate_path(target.path):
        return ExecutionResult(
            success=False,
            action=ActionType.OPEN_FILE,
            message=f"Blocked: {target.filename}",
        )

    log.info("opening_file", path=target.path)
    os.startfile(target.path)
    return ExecutionResult(
        success=True,
        action=ActionType.OPEN_FILE,
        message=f"Opened {target.filename}",
    )


def _handle_open_folder(intent: Intent, targets: list[SearchResult]) -> ExecutionResult:
    folder = intent.target
    if not folder and targets:
        folder = str(Path(targets[0].path).parent)

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

    log.info("opening_folder", path=folder)
    subprocess.Popen(["explorer.exe", folder])
    return ExecutionResult(
        success=True, action=ActionType.OPEN_FOLDER, message=f"Opened {folder}"
    )


def _handle_run_program(intent: Intent, targets: list[SearchResult]) -> ExecutionResult:
    program = intent.target
    if not program:
        return ExecutionResult(
            success=False, action=ActionType.RUN_PROGRAM, message="No program specified"
        )

    resolved = shutil.which(program)
    if not resolved:
        return ExecutionResult(
            success=False,
            action=ActionType.RUN_PROGRAM,
            message=f"Program not found: {program}",
        )

    log.info("running_program", program=resolved)
    subprocess.Popen([resolved], shell=False)
    return ExecutionResult(
        success=True, action=ActionType.RUN_PROGRAM, message=f"Launched {program}"
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
    ActionType.OPEN_FILE: _handle_open_file,
    ActionType.OPEN_FOLDER: _handle_open_folder,
    ActionType.RUN_PROGRAM: _handle_run_program,
    ActionType.SYSTEM_CONTROL: _handle_system_control,
}
