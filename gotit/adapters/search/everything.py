"""Everything CLI adapter for SearchPort — Windows file search."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from gotit.domain.models import SearchResult

if TYPE_CHECKING:
    from gotit.config import SearchConfig

log = structlog.get_logger()


class EverythingAdapter:
    def __init__(self, config: SearchConfig) -> None:
        self._es_path = config.everything_path
        self._max_results = config.max_results

    async def search(
        self, query: str, filters: dict[str, str] | None = None
    ) -> list[SearchResult]:
        es_query = _build_query(query, filters)
        log.info("everything_search", query=es_query)

        try:
            proc = await asyncio.create_subprocess_exec(
                self._es_path,
                es_query,
                "-n", str(self._max_results),
                "-sort", "date-modified-descending",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        except FileNotFoundError:
            log.error("es_exe_not_found", path=self._es_path)
            raise RuntimeError(
                f"es.exe not found at '{self._es_path}'. "
                "Download from https://www.voidtools.com/downloads/#cli and place it in PATH "
                "or set GOTIT_SEARCH__EVERYTHING_PATH."
            ) from None
        except TimeoutError:
            log.error("everything_search_timeout")
            raise RuntimeError("Everything search timed out after 10s") from None

        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace").strip()
            log.error("everything_search_error", returncode=proc.returncode, stderr=err)
            raise RuntimeError(f"Everything search failed (exit {proc.returncode}): {err}")

        lines = stdout.decode("utf-8", errors="replace").strip().splitlines()
        results = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            results.append(_path_to_search_result(line))

        log.info("everything_search_results", count=len(results))
        return results


def _build_query(query: str, filters: dict[str, str] | None) -> str:
    parts: list[str] = []

    if filters:
        if ext := filters.get("ext"):
            parts.append(f"ext:{ext}")
        if path := filters.get("path"):
            parts.append(f'path:"{path}"')
        if dm := filters.get("dm"):
            parts.append(f"dm:{dm}")

    if query and query != "*":
        ext_filter = filters.get("ext", "") if filters else ""
        if not (ext_filter and query == f"*.{ext_filter}"):
            parts.append(query)
    elif not parts:
        parts.append("*")

    return " ".join(parts)


def _path_to_search_result(filepath: str) -> SearchResult:
    p = Path(filepath)
    size = 0
    modified = None
    try:
        stat = p.stat()
        size = stat.st_size
        modified = datetime.fromtimestamp(stat.st_mtime)
    except OSError:
        pass

    return SearchResult(
        path=filepath,
        filename=p.name,
        size=size,
        modified=modified,
    )
