"""New BaseAgent + capability declaration.

An agent is anything that:
  - declares what it can do (`capabilities`)
  - picks an LLM provider + model for itself
  - exposes `handle(task, context)` to do work
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

from jarvis.llm import LLMMessage, get_provider

if TYPE_CHECKING:
    from jarvis.memory import MemoryStore


@dataclass
class Capability:
    """One thing an agent can do. Used by the router to pick an agent."""
    name: str
    description: str
    keywords: List[str] = field(default_factory=list)


@dataclass
class TaskContext:
    """Carried alongside every task. Contains conversation history,
    session id, the shared memory store, and anything else routers/
    agents need to do their job."""
    session_id: str
    user_input: str
    history: list = field(default_factory=list)
    memory: Optional["MemoryStore"] = None


class BaseAgent(ABC):
    """All Jarvis specialists subclass this."""

    name: str = "unnamed"
    description: str = ""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    system_prompt: str = "You are a helpful assistant."

    @classmethod
    def capabilities(cls) -> List[Capability]:
        return []

    async def handle(self, ctx: TaskContext) -> str:
        """Default: send the user input to the configured LLM with the
        agent's system prompt and a windowed history."""
        provider = get_provider(self.provider)
        if not provider.is_configured():
            return (
                f"[{self.name}] {self.provider} provider not configured. "
                f"Set its API key in .env."
            )

        messages: List[LLMMessage] = []
        for m in ctx.history[-10:]:
            if m.get("role") in ("user", "assistant"):
                messages.append(LLMMessage(role=m["role"], content=m["content"]))
        messages.append(LLMMessage(role="user", content=ctx.user_input))

        resp = await provider.complete(
            messages,
            model=self.model,
            system=self.system_prompt,
            max_tokens=1024,
        )
        return resp.content

    @abstractmethod
    def __init__(self) -> None: ...
