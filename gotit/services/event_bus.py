"""Async event bus for decoupled pipeline-to-UI communication."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

import structlog

from gotit.domain.events import DomainEvent

log = structlog.get_logger()

EventHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, event: DomainEvent) -> None:
        event_type = type(event)
        for handler in self._handlers.get(event_type, []):
            try:
                await handler(event)
            except Exception:
                log.exception("event_handler_error", event_type=event_type.__name__)
