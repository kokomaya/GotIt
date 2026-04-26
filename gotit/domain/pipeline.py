"""Core pipeline orchestration — wires ports together to execute voice commands."""

from __future__ import annotations

import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from gotit.adapters.activity.aliases import resolve_aliases
from gotit.domain.events import (
    ErrorEvent,
    ExecutionEvent,
    IntentEvent,
    SearchEvent,
    TranscriptEvent,
)
from gotit.domain.models import ActionType, ExecutionResult, SearchResult, Transcript

if TYPE_CHECKING:
    from gotit.domain.models import AudioChunk
    from gotit.domain.ports import ActivityStorePort, ExecutorPort, LLMPort, SearchPort, STTPort
    from gotit.services.event_bus import EventBus

log = structlog.get_logger()


class VoicePipeline:
    def __init__(
        self,
        stt: STTPort,
        llm: LLMPort,
        searcher: SearchPort,
        executor: ExecutorPort,
        event_bus: EventBus,
        activity_store: ActivityStorePort | None = None,
    ) -> None:
        self._stt = stt
        self._llm = llm
        self._searcher = searcher
        self._executor = executor
        self._bus = event_bus
        self._activity_store = activity_store

    async def run_once(self, audio: AudioChunk) -> ExecutionResult:
        transcript = await self._stt.transcribe(audio)
        await self._bus.publish(TranscriptEvent(transcript=transcript))
        return await self._run_from_transcript(transcript)

    async def run_from_text(self, text: str) -> ExecutionResult:
        transcript = Transcript(text=text)
        await self._bus.publish(TranscriptEvent(transcript=transcript))
        return await self._run_from_transcript(transcript)

    async def _run_from_transcript(self, transcript: Transcript) -> ExecutionResult:
        try:
            intent = await self._llm.parse_intent(transcript.text)
        except Exception as exc:
            log.error("intent_parse_failed", error=str(exc))
            await self._bus.publish(ErrorEvent(stage="intent", message=str(exc)))
            return ExecutionResult(
                success=False, action=ActionType.SEARCH, message=f"Intent parse failed: {exc}"
            )
        await self._bus.publish(IntentEvent(intent=intent))

        results: list[SearchResult] = []

        if intent.action in (ActionType.SEARCH, ActionType.OPEN_FILE):
            try:
                if intent.match_mode == "fuzzy":
                    results = await self._fuzzy_resolve(intent)
                else:
                    results = await self._searcher.search(
                        intent.query or intent.raw_text, intent.filters or None
                    )
            except Exception as exc:
                log.error("search_failed", error=str(exc))
                await self._bus.publish(ErrorEvent(stage="search", message=str(exc)))
                return ExecutionResult(
                    success=False, action=intent.action, message=f"Search failed: {exc}"
                )
            await self._bus.publish(SearchEvent(results=results))

        elif intent.action == ActionType.RUN_PROGRAM and intent.match_mode == "fuzzy":
            try:
                results = await self._fuzzy_resolve_program(intent)
            except Exception as exc:
                log.error("fuzzy_program_resolve_failed", error=str(exc))
            if results:
                await self._bus.publish(SearchEvent(results=results))

        try:
            result = await self._executor.execute(intent, results)
        except Exception as exc:
            log.error("execution_failed", error=str(exc))
            await self._bus.publish(ErrorEvent(stage="execution", message=str(exc)))
            return ExecutionResult(
                success=False, action=intent.action, message=f"Execution failed: {exc}"
            )
        await self._bus.publish(ExecutionEvent(result=result))
        return result

    # -- Fuzzy resolution chain (files) --

    async def _fuzzy_resolve(self, intent) -> list[SearchResult]:
        hints = intent.fuzzy_hints or {}

        # Strategy 1: activity history
        results = await self._strategy_activity_history(intent, hints)
        if results:
            log.info("fuzzy_resolved", strategy="activity_history", count=len(results))
            return results

        # Strategy 2: Everything + synonyms
        results = await self._strategy_synonyms(intent, hints)
        if results:
            log.info("fuzzy_resolved", strategy="synonyms", count=len(results))
            return results

        # Strategy 3: relaxed search
        results = await self._strategy_relaxed(intent, hints)
        if results:
            log.info("fuzzy_resolved", strategy="relaxed", count=len(results))
            return results

        log.warning("fuzzy_resolve_exhausted", query=intent.query)
        return []

    async def _strategy_activity_history(self, intent, hints: dict) -> list[SearchResult]:
        if not self._activity_store:
            return []

        time_range = _time_ref_to_range(hints.get("time_ref"))
        extensions = hints.get("likely_ext")
        query = hints.get("partial_name") or intent.query or hints.get("description")
        if not query or query == "*":
            if extensions and time_range:
                query = "%"
            else:
                return []

        records = await self._activity_store.search_files(
            query=query, time_range=time_range, extensions=extensions, limit=20
        )
        return [
            SearchResult(path=r.path, filename=r.name, modified=r.last_opened)
            for r in records
        ]

    async def _strategy_synonyms(self, intent, hints: dict) -> list[SearchResult]:
        queries: list[str] = []
        if intent.query and intent.query != "*":
            queries.append(intent.query)
        queries.extend(hints.get("synonyms") or [])
        if not queries:
            return []

        likely_ext = hints.get("likely_ext") or []
        seen: set[str] = set()
        all_results: list[SearchResult] = []

        for q in queries:
            if likely_ext:
                for ext in likely_ext:
                    filters = {**intent.filters, "ext": ext}
                    for r in await self._searcher.search(q, filters):
                        if r.path not in seen:
                            seen.add(r.path)
                            all_results.append(r)
            else:
                for r in await self._searcher.search(q, intent.filters or None):
                    if r.path not in seen:
                        seen.add(r.path)
                        all_results.append(r)

            if len(all_results) >= 20:
                break

        return all_results[:20]

    async def _strategy_relaxed(self, intent, hints: dict) -> list[SearchResult]:
        partial = hints.get("partial_name")
        if partial:
            results = await self._searcher.search(f"*{partial}*", None)
            if results:
                return results

        if intent.filters and intent.query:
            results = await self._searcher.search(intent.query, None)
            if results:
                return results

        return []

    # -- Fuzzy resolution chain (programs) --

    async def _fuzzy_resolve_program(self, intent) -> list[SearchResult]:
        hints = intent.fuzzy_hints or {}
        target = intent.target or ""

        candidates = resolve_aliases(target)
        candidates.extend(hints.get("synonyms") or [])
        candidates = list(dict.fromkeys(candidates))

        # Try activity history
        if self._activity_store and candidates:
            for name in candidates:
                records = await self._activity_store.search_programs(name, limit=5)
                if records:
                    r = records[0]
                    if Path(r.path).is_file():
                        log.info("fuzzy_program_resolved", source="activity", path=r.path)
                        return [SearchResult(path=r.path, filename=r.name)]

        # Try shutil.which
        for name in candidates:
            resolved = shutil.which(name)
            if resolved:
                log.info("fuzzy_program_resolved", source="which", path=resolved)
                return [SearchResult(path=resolved, filename=Path(resolved).name)]

        return []


def _time_ref_to_range(time_ref: str | None) -> tuple[datetime, datetime] | None:
    if not time_ref:
        return None

    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    mapping: dict[str, tuple[datetime, datetime]] = {
        "today": (today_start, now),
        "yesterday": (today_start - timedelta(days=1), today_start),
        "this_week": (today_start - timedelta(days=today_start.weekday()), now),
        "last_week": (
            today_start - timedelta(days=today_start.weekday() + 7),
            today_start - timedelta(days=today_start.weekday()),
        ),
        "this_month": (today_start.replace(day=1), now),
        "last_month": (
            (today_start.replace(day=1) - timedelta(days=1)).replace(day=1),
            today_start.replace(day=1),
        ),
        "recent": (now - timedelta(hours=2), now),
    }

    return mapping.get(time_ref)
