"""Dependency injection container — assembles adapters into a pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gotit.domain.pipeline import VoicePipeline
from gotit.services.event_bus import EventBus

if TYPE_CHECKING:
    from gotit.config import AppConfig


class _StubSTT:
    """Placeholder STT for text-only mode — avoids loading whisper model."""

    async def transcribe(self, audio):
        raise RuntimeError("STT not available. Use --text mode or provide a whisper model.")

    async def start_stream(self):
        raise NotImplementedError
        yield

    async def stop_stream(self):
        pass


class Container:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.event_bus = EventBus()

    def build_pipeline(self, *, require_stt: bool = True) -> VoicePipeline:
        return VoicePipeline(
            stt=self._build_stt() if require_stt else _StubSTT(),
            llm=self._build_llm(),
            searcher=self._build_searcher(),
            executor=self._build_executor(),
            event_bus=self.event_bus,
        )

    def _build_stt(self):
        from gotit.adapters.stt.whisper_cpp import WhisperCppAdapter

        return WhisperCppAdapter(self.config.stt)

    def _build_llm(self):
        if self.config.llm.provider == "ollama":
            from gotit.adapters.llm.ollama import OllamaAdapter

            return OllamaAdapter(self.config.llm)

        from gotit.adapters.llm.claude import OpenAICompatibleAdapter

        return OpenAICompatibleAdapter(self.config.llm)

    def _build_searcher(self):
        from gotit.adapters.search.everything import EverythingAdapter

        return EverythingAdapter(self.config.search)

    def _build_executor(self):
        from gotit.adapters.executor.windows import WindowsExecutor

        return WindowsExecutor(search_config=self.config.search)
