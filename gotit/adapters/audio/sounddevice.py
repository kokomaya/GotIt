"""sounddevice adapter for AudioCapturePort — real-time audio capture."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

import numpy as np
import sounddevice as sd
import structlog

from gotit.domain.models import AudioChunk, AudioDevice

if TYPE_CHECKING:
    from gotit.config import AudioConfig

log = structlog.get_logger()

_DEFAULT_SAMPLE_RATE = 16000
_DEFAULT_CHANNELS = 1
_VAD_SILENCE_THRESHOLD = 0.01
_VAD_SILENCE_DURATION = 1.5


class SoundDeviceAdapter:
    def __init__(self, config: AudioConfig) -> None:
        self._sample_rate = config.sample_rate or _DEFAULT_SAMPLE_RATE
        self._channels = config.channels or _DEFAULT_CHANNELS
        self._device_index = config.device_index
        self._recording = False
        self._audio_queue: asyncio.Queue[np.ndarray | None] = asyncio.Queue()

    async def start(self) -> AsyncIterator[AudioChunk]:
        self._recording = True
        loop = asyncio.get_running_loop()

        def callback(indata: np.ndarray, frames: int, time_info, status) -> None:
            if status:
                log.warning("audio_callback_status", status=str(status))
            if self._recording:
                loop.call_soon_threadsafe(self._audio_queue.put_nowait, indata.copy())

        stream = sd.InputStream(
            samplerate=self._sample_rate,
            channels=self._channels,
            dtype="float32",
            device=self._device_index,
            blocksize=int(self._sample_rate * 0.1),
            callback=callback,
        )

        with stream:
            log.info("audio_capture_started", sample_rate=self._sample_rate)
            while self._recording:
                try:
                    data = await asyncio.wait_for(self._audio_queue.get(), timeout=0.5)
                except TimeoutError:
                    continue
                if data is None:
                    break
                yield AudioChunk(
                    data=data.tobytes(),
                    sample_rate=self._sample_rate,
                    timestamp=time.time(),
                )

    async def stop(self) -> None:
        self._recording = False
        self._audio_queue.put_nowait(None)
        log.info("audio_capture_stopped")

    def list_devices(self) -> list[AudioDevice]:
        devices = sd.query_devices()
        result = []
        default_input = sd.default.device[0]
        for i, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                result.append(
                    AudioDevice(
                        index=i,
                        name=dev["name"],
                        is_default=(i == default_input),
                    )
                )
        return result


def record_until_silence(
    config: AudioConfig,
    silence_threshold: float = _VAD_SILENCE_THRESHOLD,
    silence_duration: float = _VAD_SILENCE_DURATION,
) -> AudioChunk:
    """Synchronous blocking record: captures audio until silence is detected."""
    sample_rate = config.sample_rate or _DEFAULT_SAMPLE_RATE
    channels = config.channels or _DEFAULT_CHANNELS
    device = config.device_index

    chunks: list[np.ndarray] = []
    silent_start: float | None = None

    def callback(indata: np.ndarray, frames: int, time_info, status) -> None:
        nonlocal silent_start
        chunks.append(indata.copy())
        rms = float(np.sqrt(np.mean(indata**2)))
        if rms < silence_threshold:
            if silent_start is None:
                silent_start = time.time()
            elif time.time() - silent_start >= silence_duration:
                raise sd.CallbackAbort
        else:
            silent_start = None

    log.info("recording_started", device=device)
    try:
        with sd.InputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype="float32",
            device=device,
            blocksize=int(sample_rate * 0.1),
            callback=callback,
        ):
            while True:
                sd.sleep(100)
    except sd.CallbackAbort:
        pass

    if not chunks:
        return AudioChunk(data=b"", sample_rate=sample_rate, timestamp=time.time())

    audio_data = np.concatenate(chunks)
    log.info("recording_finished", duration_s=round(len(audio_data) / sample_rate, 2))
    return AudioChunk(
        data=audio_data.tobytes(),
        sample_rate=sample_rate,
        timestamp=time.time(),
    )
