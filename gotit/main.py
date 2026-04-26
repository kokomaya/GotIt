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
    sub = parser.add_subparsers(dest="command")

    # Default mode (no subcommand)
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

    # filter subcommand
    filter_parser = sub.add_parser("filter", help="Manage search result filter rules")
    filter_sub = filter_parser.add_subparsers(dest="filter_action")

    filter_sub.add_parser("list", help="Show current filter rules")

    add_parser = filter_sub.add_parser("add", help="Add a filter rule")
    add_parser.add_argument("type", choices=["path", "filename", "ext"], help="Rule type")
    add_parser.add_argument("value", help="Value to exclude (e.g. .git, ~$*, pyc)")

    rm_parser = filter_sub.add_parser("remove", help="Remove a filter rule")
    rm_parser.add_argument("type", choices=["path", "filename", "ext"], help="Rule type")
    rm_parser.add_argument("value", help="Value to remove")

    filter_sub.add_parser("path", help="Show filters.yaml file path")

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


def _run_filter(args: argparse.Namespace, config: AppConfig) -> None:
    from pathlib import Path

    from gotit.services.filter_rules import FilterRules

    rules_path = config.search.filter_rules_path
    resolved_path = Path(rules_path).expanduser()
    rules = FilterRules.load(rules_path)

    _TYPE_MAP = {
        "path": ("excluded_paths", rules.excluded_paths),
        "filename": ("excluded_filenames", rules.excluded_filenames),
        "ext": ("excluded_extensions", rules.excluded_extensions),
    }

    if args.filter_action == "list" or args.filter_action is None:
        print(f"Filter rules ({resolved_path}):\n")
        print("Excluded paths:")
        for p in rules.excluded_paths:
            print(f"  - {p}")
        print("\nExcluded filenames:")
        for f in rules.excluded_filenames:
            print(f"  - {f}")
        print("\nExcluded extensions:")
        for e in rules.excluded_extensions:
            print(f"  - {e}")
        return

    if args.filter_action == "path":
        print(resolved_path)
        return

    if args.filter_action == "add":
        _, lst = _TYPE_MAP[args.type]
        if args.value in lst:
            print(f"Already exists: {args.value}")
            return
        lst.append(args.value)
        rules.save(rules_path)
        print(f"Added {args.type} filter: {args.value}")
        return

    if args.filter_action == "remove":
        _, lst = _TYPE_MAP[args.type]
        if args.value not in lst:
            print(f"Not found: {args.value}")
            return
        lst.remove(args.value)
        rules.save(rules_path)
        print(f"Removed {args.type} filter: {args.value}")


def main() -> None:
    args = _parse_args()
    config = AppConfig()

    if args.command == "filter":
        _run_filter(args, config)
        return

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
