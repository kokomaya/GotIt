"""OpenAI-compatible LLM adapter for LLMPort."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from gotit.domain.models import ActionType, Intent

if TYPE_CHECKING:
    from gotit.config import LLMConfig

log = structlog.get_logger()

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_SYSTEM_PROMPT = (_PROMPTS_DIR / "intent_system.txt").read_text(encoding="utf-8")


class OpenAICompatibleAdapter:
    """LLM adapter using any OpenAI-compatible API."""

    def __init__(self, config: LLMConfig) -> None:
        import httpx
        import openai

        self._model = config.model
        self._fallback_models = config.fallback_models
        self._client = openai.OpenAI(
            api_key=config.api_key or None,
            base_url=config.base_url or None,
            default_headers=config.extra_headers or None,
            http_client=httpx.Client(verify=False),
        )
        self._context: list[str] = []
        self._max_context = 3

    async def parse_intent(
        self, text: str, context: list[str] | None = None
    ) -> Intent:
        ctx = context if context is not None else self._context

        user_content = text
        if ctx:
            history = "\n".join(f"- {c}" for c in ctx[-self._max_context :])
            user_content = f"Recent commands:\n{history}\n\nCurrent command: {text}"

        models_to_try = [self._model, *self._fallback_models]
        raw = ""

        for model in models_to_try:
            if not model:
                continue
            log.debug("llm_request", model=model, text=text)
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                )
                raw = (response.choices[0].message.content or "").strip()
                if raw:
                    log.debug("llm_response", model=model, raw=raw)
                    break
                log.warning("llm_empty_response", model=model)
            except Exception as exc:
                log.warning("llm_model_failed", model=model, error=str(exc))

        if not raw:
            log.error("llm_all_models_failed", models=models_to_try)
            raise RuntimeError("All LLM models returned empty responses")

        intent = _parse_response(raw, text)

        self._context.append(text)
        if len(self._context) > self._max_context:
            self._context.pop(0)

        return intent


ClaudeAdapter = OpenAICompatibleAdapter


def _parse_response(raw: str, original_text: str) -> Intent:
    cleaned = raw
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        log.warning("llm_json_parse_failed", raw=raw)
        return Intent(
            action=ActionType.SEARCH,
            raw_text=original_text,
            query=original_text,
            confidence=0.3,
        )

    try:
        action = ActionType(data["action"])
    except (KeyError, ValueError):
        action = ActionType.SEARCH

    return Intent(
        action=action,
        raw_text=original_text,
        query=data.get("query"),
        target=data.get("target"),
        filters={k: v for k, v in data.get("filters", {}).items() if v},
        confidence=float(data.get("confidence", 0.5)),
        match_mode=data.get("match_mode", "exact"),
        fuzzy_hints=data.get("fuzzy_hints"),
        with_program=data.get("with_program"),
    )
