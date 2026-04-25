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
    result = await pipeline.run_from_text(text)

    if result.success:
        print(f"\n[OK] {result.message}")
    else:
        print(f"\n[FAIL] {result.message}", file=sys.stderr)


def main() -> None:
    args = _parse_args()
    config = AppConfig()
    configure_logging(debug=args.debug or config.debug)

    log = structlog.get_logger()
    log.info("GotIt starting...", version="0.1.0")

    if args.text:
        asyncio.run(_run_text(config, args.text))
    elif args.mode == "server":
        log.info("server_mode", host=config.server.host, port=config.server.port)
        log.warning("server_mode_not_yet_implemented")
    else:
        log.info("cli_mode", hint="Use --text 'your command' to run a text command")


if __name__ == "__main__":
    main()
