"""REST API routes — config, devices, history, health."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api")

_start_time = time.time()


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": "0.1.0",
        "uptime_s": round(time.time() - _start_time, 1),
    }


@router.get("/config")
async def get_config(request: Request) -> dict[str, Any]:
    cfg = request.app.state.app_state.config
    return {
        "stt": {"engine": cfg.stt.engine, "language": cfg.stt.language},
        "llm": {"provider": cfg.llm.provider, "model": cfg.llm.model},
        "search": {"max_results": cfg.search.max_results},
        "audio": {"sample_rate": cfg.audio.sample_rate},
        "ui": {"auto_close_delay": cfg.ui.auto_close_delay},
    }


@router.get("/devices")
async def list_devices(request: Request) -> list[dict[str, Any]]:
    from gotit.adapters.audio.sounddevice import SoundDeviceAdapter

    cfg = request.app.state.app_state.config
    adapter = SoundDeviceAdapter(cfg.audio)
    devices = adapter.list_devices()
    return [{"index": d.index, "name": d.name, "is_default": d.is_default} for d in devices]


@router.get("/history")
async def get_history(request: Request) -> list[dict[str, Any]]:
    return request.app.state.app_state.session.get_history()
