"""Session management — tracks pipeline execution history."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SessionRecord:
    input_text: str
    intent_action: str | None = None
    intent_query: str | None = None
    result_count: int = 0
    success: bool = False
    message: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SessionManager:
    def __init__(self, max_history: int = 50) -> None:
        self._history: deque[SessionRecord] = deque(maxlen=max_history)

    def record(self, entry: SessionRecord) -> None:
        self._history.appendleft(entry)

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return [r.to_dict() for r in list(self._history)[:limit]]

    def get_input_history(self, limit: int = 20) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for r in self._history:
            if r.input_text not in seen:
                seen.add(r.input_text)
                result.append(r.input_text)
                if len(result) >= limit:
                    break
        return result

    def clear(self) -> None:
        self._history.clear()
