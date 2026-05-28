"""Provider-agnostic LLM interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    raw: object = field(default=None, repr=False)


class LLMProvider(ABC):
    """Abstract LLM backend. Implementations go in this package."""

    name: str = "abstract"

    @abstractmethod
    async def complete(
        self,
        messages: List[LLMMessage],
        *,
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: Optional[str] = None,
    ) -> LLMResponse:
        """Run a chat completion and return the assistant's reply."""
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if this provider has the env vars it needs."""
        ...

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<LLMProvider {self.name} configured={self.is_configured()}>"
