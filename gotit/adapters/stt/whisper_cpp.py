"""whisper.cpp adapter for STTPort — local, offline speech-to-text."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import structlog

from gotit.domain.models import Transcript

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from gotit.config import STTConfig
    from gotit.domain.models import AudioChunk

log = structlog.get_logger()


class WhisperCppAdapter:
    def __init__(self, config: STTConfig) -> None:
        self._model_path = config.model_path
        self._language = config.language
        self._model = None
        self._load_model()

    def _load_model(self) -> None:
        model_file = Path(self._model_path)
        if not model_file.exists():
            log.warning(
                "whisper_model_not_found",
                path=self._model_path,
                hint="Run: uv run python scripts/download_model.py base",
            )
            return

        from pywhispercpp.model import Model

        self._model = Model(str(model_file), print_realtime=False, print_progress=False)
        log.info("whisper_model_loaded", path=self._model_path, language=self._language)

    async def transcribe(self, audio: AudioChunk) -> Transcript:
        if self._model is None:
            raise RuntimeError(
                f"Whisper model not loaded. Place model at '{self._model_path}' "
                "or run: uv run python scripts/download_model.py base"
            )

        pcm = _bytes_to_float32(audio.data, audio.sample_rate)

        segments = self._model.transcribe(pcm, language=self._language)
        text = " ".join(seg.text.strip() for seg in segments).strip()

        log.info("stt_result", text=text, segments=len(segments))
        return Transcript(text=text, language=self._language)

    async def start_stream(self) -> AsyncIterator[Transcript]:
        raise NotImplementedError("Streaming STT not yet available")
        yield  # make it a generator

    async def stop_stream(self) -> None:
        pass


def _bytes_to_float32(data: bytes, sample_rate: int) -> np.ndarray:
    """Convert raw audio bytes to float32 numpy array expected by whisper.cpp."""
    if len(data) == 0:
        return np.array([], dtype=np.float32)

    sample_width = len(data) // (len(data) // 4) if len(data) >= 4 else 4

    if sample_width == 4:
        arr = np.frombuffer(data, dtype=np.float32)
    elif sample_width == 2:
        arr = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
    else:
        arr = np.frombuffer(data, dtype=np.float32)

    return arr
