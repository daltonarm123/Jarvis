"""OpenAI provider."""

from __future__ import annotations

import os
from typing import List, Optional

from .base import LLMMessage, LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self) -> None:
        self._client = None

    def is_configured(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    def _get_client(self):
        if self._client is None:
            if not self.is_configured():
                raise RuntimeError("OPENAI_API_KEY not set")
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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
        payload = []
        if system:
            payload.append({"role": "system", "content": system})
        payload.extend({"role": m.role, "content": m.content} for m in messages)

        resp = await client.chat.completions.create(
            model=model,
            messages=payload,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        choice = resp.choices[0].message
        usage = getattr(resp, "usage", None)
        return LLMResponse(
            content=(choice.content or "").strip(),
            model=model,
            provider=self.name,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            raw=resp,
        )
