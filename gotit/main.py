"""GotIt application entry point."""

from __future__ import annotations

import logging
import sys

import structlog

from gotit.config import AppConfig


def configure_logging(*, debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )


def main() -> None:
    config = AppConfig()
    configure_logging(debug=config.debug)

    log = structlog.get_logger()
    log.info("GotIt starting...", version="0.1.0", debug=config.debug)


if __name__ == "__main__":
    main()
