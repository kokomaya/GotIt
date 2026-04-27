"""Learned mappings — records successful command→file resolutions for LLM few-shot."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
import yaml

log = structlog.get_logger()

_MAX_MAPPINGS = 50


@dataclass
class LearnedMapping:
    input_text: str
    resolved_path: str
    action: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LearnedMappingStore:
    def __init__(self, path: str = "~/.gotit/learned_mappings.yaml") -> None:
        self._path = Path(path).expanduser()
        self._mappings: list[LearnedMapping] = []
        self._load()

    def _load(self) -> None:
        if not self._path.is_file():
            return
        try:
            with open(self._path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for item in data.get("mappings", []):
                self._mappings.append(LearnedMapping(**item))
        except Exception:
            log.warning("learned_mappings_load_failed", path=str(self._path))

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {"mappings": [m.to_dict() for m in self._mappings]}
        with open(self._path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def record(self, input_text: str, resolved_path: str, action: str) -> None:
        input_norm = input_text.strip().lower()
        for existing in self._mappings:
            if existing.input_text.strip().lower() == input_norm:
                existing.resolved_path = resolved_path
                existing.action = action
                existing.timestamp = datetime.now().isoformat()
                self._save()
                return

        self._mappings.append(
            LearnedMapping(
                input_text=input_text.strip(),
                resolved_path=resolved_path,
                action=action,
            )
        )
        if len(self._mappings) > _MAX_MAPPINGS:
            self._mappings = self._mappings[-_MAX_MAPPINGS:]
        self._save()
        log.info("learned_mapping_recorded", input=input_text, path=resolved_path)

    def get_recent(self, limit: int = 10) -> list[LearnedMapping]:
        return list(reversed(self._mappings[-limit:]))

    def to_prompt_section(self, limit: int = 10) -> str:
        recent = self.get_recent(limit)
        if not recent:
            return ""

        lines = [
            "\n## Recent successful commands (learned from this user's history)",
            "",
            "Use these to understand the user's naming patterns and file locations:",
            "",
        ]
        for m in recent:
            filename = Path(m.resolved_path).name
            lines.append(f'- "{m.input_text}" → {m.action} {filename} ({m.resolved_path})')

        return "\n".join(lines)
