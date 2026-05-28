"""Anthropic provider."""

from __future__ import annotations

import os
from typing import List, Optional

from .base import LLMMessage, LLMProvider, LLMResponse


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self) -> None:
        self._client = None

    def is_configured(self) -> bool:
        return bool(os.getenv("ANTHROPIC_API_KEY"))

    def _get_client(self):
        if self._client is None:
            if not self.is_configured():
                raise RuntimeError("ANTHROPIC_API_KEY not set")
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        return self._client

    async def complete(
        self,
        messages: List[LLMMessage],
        *,
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: Optional[str] = None,
    ) -> LLMResponse:
        client = self._get_client()
        # Anthropic takes `system` as a top-level arg, not a message role.
        anth_messages = [{"role": m.role, "content": m.content} for m in messages]
        kwargs = dict(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=anth_messages,
        )
        if system:
            kwargs["system"] = system

        resp = await client.messages.create(**kwargs)
        # Anthropic returns content as a list of blocks; concatenate text blocks.
        text_parts = [
            getattr(block, "text", "") for block in resp.content if getattr(block, "type", None) == "text"
        ]
        usage = getattr(resp, "usage", None)
        return LLMResponse(
            content="".join(text_parts).strip(),
            model=model,
            provider=self.name,
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
            raw=resp,
        )
