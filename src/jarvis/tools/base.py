"""Tool base classes + registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class ToolError(Exception):
    """Raised when a tool fails in a recoverable, agent-visible way."""


@dataclass
class ToolResult:
    """What a tool returns. `ok=False` means the tool ran but produced
    a failure (don't raise — the agent should see the message)."""
    ok: bool
    output: Any = None
    error: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_text(self) -> str:
        if not self.ok:
            return f"ERROR: {self.error}"
        if isinstance(self.output, str):
            return self.output
        return repr(self.output)


class Tool(ABC):
    """Abstract tool. Subclass to add a new capability."""

    name: str = "unnamed"
    description: str = ""
    # JSON schema for parameters (OpenAI function-calling shape).
    parameters: Dict[str, Any] = {"type": "object", "properties": {}}

    @abstractmethod
    async def run(self, **kwargs) -> ToolResult: ...

    # ---- LLM function-calling helpers ----

    def to_openai_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_anthropic_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }


class ToolRegistry:
    """Holds a set of tools available to an agent (or globally)."""

    def __init__(self, tools: Optional[List[Tool]] = None) -> None:
        self._tools: Dict[str, Tool] = {}
        for t in tools or []:
            self.register(t)

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise ToolError(f"Unknown tool: {name}")
        return self._tools[name]

    def names(self) -> List[str]:
        return sorted(self._tools)

    def all(self) -> List[Tool]:
        return list(self._tools.values())

    def openai_schemas(self) -> List[Dict[str, Any]]:
        return [t.to_openai_schema() for t in self._tools.values()]

    def anthropic_schemas(self) -> List[Dict[str, Any]]:
        return [t.to_anthropic_schema() for t in self._tools.values()]

    async def call(self, name: str, **kwargs) -> ToolResult:
        tool = self.get(name)
        try:
            return await tool.run(**kwargs)
        except ToolError as e:
            return ToolResult(ok=False, error=str(e))
        except Exception as e:  # pragma: no cover - defensive
            return ToolResult(ok=False, error=f"{type(e).__name__}: {e}")
