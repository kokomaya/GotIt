"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gotit.api.dependencies import _AppState
from gotit.api.routes import router
from gotit.api.websocket import ws_router
from gotit.services.container import Container
from gotit.services.session import SessionManager

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from gotit.config import AppConfig

log = structlog.get_logger()


def create_app(config: AppConfig) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container = Container(config)
        pipeline = container.build_pipeline(require_stt=False)
        session = SessionManager()

        tracker = container.build_tracker()
        if tracker:
            await tracker.start()

        app.state.app_state = _AppState(
            config=config,
            pipeline=pipeline,
            event_bus=container.event_bus,
            session=session,
        )
        log.info("server_ready", host=config.server.host, port=config.server.port)

        try:
            yield
        finally:
            if tracker:
                await tracker.stop()
            if container.activity_store:
                await container.activity_store.close()

    app = FastAPI(title="GotIt", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "tauri://localhost"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    app.include_router(ws_router)

    return app
