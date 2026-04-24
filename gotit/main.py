"""GotIt application entry point."""

import structlog

log = structlog.get_logger()


def main() -> None:
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(0),
    )
    log.info("GotIt starting...", version="0.1.0")


if __name__ == "__main__":
    main()
