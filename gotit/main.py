"""GotIt application entry point."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

import structlog

from gotit.config import AppConfig


def configure_logging(*, debug: bool = False) -> None:
    import io

    level = logging.DEBUG if debug else logging.INFO
    log_output = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=log_output),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GotIt — voice-driven local AI assistant")
    parser.add_argument(
        "--text", "-t",
        type=str,
        help="Run a single text command (skip voice input)",
    )
    parser.add_argument(
        "--mode",
        choices=["cli", "server"],
        default="cli",
        help="Run mode: cli (default) or server (FastAPI)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


async def _run_text(config: AppConfig, text: str) -> None:
    log = structlog.get_logger()

    from gotit.services.container import Container

    container = Container(config)
    pipeline = container.build_pipeline(require_stt=False)

    log.info("processing_text", text=text)
    try:
        result = await pipeline.run_from_text(text)

        if result.success:
            print(f"\n[OK] {result.message}")
        else:
            print(f"\n[FAIL] {result.message}", file=sys.stderr)
    finally:
        if container.activity_store:
            await container.activity_store.close()


def _run_server(config: AppConfig) -> None:
    import uvicorn

    from gotit.app import create_app

    app = create_app(config)
    uvicorn.run(app, host=config.server.host, port=config.server.port)


def main() -> None:
    args = _parse_args()
    config = AppConfig()
    configure_logging(debug=args.debug or config.debug)

    log = structlog.get_logger()
    log.info("GotIt starting...", version="0.1.0")

    if args.text:
        asyncio.run(_run_text(config, args.text))
    elif args.mode == "server":
        _run_server(config)
    else:
        log.info("cli_mode", hint="Use --text 'your command' or --mode server")


if __name__ == "__main__":
    main()
