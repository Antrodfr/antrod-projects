"""Base Agent class with Mistral and OpenAI support."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from orchestrator.config import (
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    get_api_key,
)

logger = logging.getLogger(__name__)


@dataclass
class Agent:
    """A single LLM-powered agent with a specific role.

    Args:
        name: Human-readable agent name (e.g. "Researcher").
        role: System prompt that defines the agent's behaviour.
        provider: ``"mistral"`` or ``"openai"``.
        model: Model identifier (falls back to DEFAULT_MODEL).
        temperature: Sampling temperature.
    """

    name: str
    role: str
    provider: str = DEFAULT_PROVIDER
    model: str = DEFAULT_MODEL
    temperature: float = 0.7
    _client: Any = field(default=None, repr=False, init=False)

    # ── public API ───────────────────────────────────────────

    async def run(self, input_text: str) -> str:
        """Send *input_text* to the LLM and return the response string."""
        logger.info("[%s] running  (model=%s)", self.name, self.model)
        logger.debug("[%s] input:\n%s", self.name, input_text[:200])

        try:
            if self.provider == "mistral":
                return await self._call_mistral(input_text)
            return await self._call_openai(input_text)
        except Exception as exc:
            logger.error("[%s] LLM call failed: %s", self.name, exc)
            raise RuntimeError(f"Agent '{self.name}' failed: {exc}") from exc

    # ── provider implementations ─────────────────────────────

    async def _call_mistral(self, text: str) -> str:
        from mistralai import Mistral

        client = Mistral(api_key=get_api_key("mistral"))
        response = await client.chat.complete_async(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": self.role},
                {"role": "user", "content": text},
            ],
        )
        return response.choices[0].message.content

    async def _call_openai(self, text: str) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=get_api_key("openai"))
        response = await client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": self.role},
                {"role": "user", "content": text},
            ],
        )
        return response.choices[0].message.content
