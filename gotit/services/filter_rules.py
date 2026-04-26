"""Search result filter rules — load/save/match against YAML config."""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

import structlog
import yaml

log = structlog.get_logger()

DEFAULT_EXCLUDED_PATHS = [
    ".git", ".svn", ".hg",
    "node_modules",
    "__pycache__", ".venv", ".tox", ".mypy_cache", ".ruff_cache",
    "$RECYCLE.BIN", "System Volume Information",
    ".vs", ".idea",
]

DEFAULT_EXCLUDED_FILENAMES = [
    "desktop.ini", "thumbs.db",
    "~$*",
]

DEFAULT_EXCLUDED_EXTENSIONS = [
    "pyc", "pyo", "obj", "o", "lib",
    "tmp", "bak",
]


@dataclass
class FilterRules:
    excluded_paths: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDED_PATHS))
    excluded_filenames: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDED_FILENAMES))
    excluded_extensions: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDED_EXTENSIONS))

    def __post_init__(self) -> None:
        self._excluded_ext_set = {e.lower() for e in self.excluded_extensions}

    @classmethod
    def load(cls, path: str = "~/.gotit/filters.yaml") -> FilterRules:
        resolved = Path(path).expanduser()
        if not resolved.is_file():
            rules = cls()
            rules.save(path)
            log.info("filter_rules_created", path=str(resolved))
            return rules

        with open(resolved, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        rules = cls(
            excluded_paths=data.get("excluded_paths", DEFAULT_EXCLUDED_PATHS),
            excluded_filenames=data.get("excluded_filenames", DEFAULT_EXCLUDED_FILENAMES),
            excluded_extensions=data.get("excluded_extensions", DEFAULT_EXCLUDED_EXTENSIONS),
        )
        log.info("filter_rules_loaded", path=str(resolved))
        return rules

    def save(self, path: str = "~/.gotit/filters.yaml") -> None:
        resolved = Path(path).expanduser()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "excluded_paths": self.excluded_paths,
            "excluded_filenames": self.excluded_filenames,
            "excluded_extensions": self.excluded_extensions,
        }
        with open(resolved, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def should_exclude(self, filepath: str) -> bool:
        p = Path(filepath)

        parts = {part.lower() for part in p.parts}
        for excluded in self.excluded_paths:
            if excluded.lower() in parts:
                return True

        name = p.name.lower()
        for pattern in self.excluded_filenames:
            if fnmatch(name, pattern.lower()):
                return True

        ext = p.suffix.lstrip(".").lower()
        if ext and ext in self._excluded_ext_set:
            return True

        return False

    def to_everything_excludes(self) -> list[str]:
        return [f"!path:{p}" for p in self.excluded_paths]
