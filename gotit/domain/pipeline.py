"""Core pipeline orchestration — wires ports together to execute voice commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from gotit.domain.events import (
    ErrorEvent,
    ExecutionEvent,
    IntentEvent,
    SearchEvent,
    TranscriptEvent,
)
from gotit.domain.models import ActionType, ExecutionResult, Transcript

if TYPE_CHECKING:
    from gotit.domain.models import AudioChunk
    from gotit.domain.ports import ExecutorPort, LLMPort, SearchPort, STTPort
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
    ) -> None:
        self._stt = stt
        self._llm = llm
        self._searcher = searcher
        self._executor = executor
        self._bus = event_bus

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

        results = []
        if intent.action in (ActionType.SEARCH, ActionType.OPEN_FILE):
            try:
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
