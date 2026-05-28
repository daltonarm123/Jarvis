"""BaseAgent + Capability + TaskContext + tool-use loop.

Agents now have:
  - declarative capabilities (router uses them)
  - LLM provider/model (each agent picks its own)
  - an optional ToolRegistry (gives the agent real-world abilities)

If `tools` is set, `handle()` runs a tool-use loop:
  user message → LLM → maybe tool calls → run tools → feed back → … → final text
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from jarvis.llm import LLMMessage, get_provider

if TYPE_CHECKING:
    from jarvis.memory import MemoryStore
    from jarvis.tools import ToolRegistry


@dataclass
class Capability:
    name: str
    description: str
    keywords: List[str] = field(default_factory=list)


@dataclass
class TaskContext:
    session_id: str
    user_input: str
    history: List[Dict[str, Any]] = field(default_factory=list)
    memory: Optional["MemoryStore"] = None
    tools: Optional["ToolRegistry"] = None


# Max tool-use rounds per turn — prevents runaway loops.
MAX_TOOL_ROUNDS = 6


class BaseAgent(ABC):
    name: str = "unnamed"
    description: str = ""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    system_prompt: str = "You are a helpful assistant."

    # If non-None, the agent will use these tools instead of `ctx.tools`.
    # Subclasses set this in __init__ when they want their own toolset.
    tools: Optional["ToolRegistry"] = None

    @classmethod
    def capabilities(cls) -> List[Capability]:
        return []

    async def handle(self, ctx: TaskContext) -> str:
        provider = get_provider(self.provider)
        if not provider.is_configured():
            return (
                f"[{self.name}] {self.provider} provider not configured. "
                f"Set its API key in .env."
            )

        # Pick the tool registry to expose
        tools = self.tools or ctx.tools

        messages: List[LLMMessage] = []
        for m in ctx.history[-10:]:
            if m.get("role") in ("user", "assistant"):
                messages.append(LLMMessage(role=m["role"], content=m["content"]))
        messages.append(LLMMessage(role="user", content=ctx.user_input))

        # No tools? Plain completion.
        if not tools or not tools.all():
            resp = await provider.complete(
                messages, model=self.model, system=self.system_prompt, max_tokens=1024
            )
            return resp.content

        # Tool-using loop. We do this via a simple "ask LLM to emit JSON
        # tool calls in a fenced block, parse, execute, feed result back".
        # This is provider-agnostic — works without native function-calling
        # support and is good enough for our needs at this stage. Native
        # function-calling can be added per-provider later.
        sys_prompt = self._build_tool_system_prompt(tools)
        for round_idx in range(MAX_TOOL_ROUNDS):
            resp = await provider.complete(
                messages,
                model=self.model,
                system=sys_prompt,
                max_tokens=1500,
                temperature=0.3,
            )
            reply = resp.content
            calls = _extract_tool_calls(reply)

            if not calls:
                return reply  # final answer

            # Run tools, feed results back as a user-role message.
            tool_outputs: List[str] = []
            for call in calls:
                name = call.get("tool")
                args = call.get("args") or {}
                if not isinstance(args, dict):
                    tool_outputs.append(f"<tool {name} error>args must be an object</tool>")
                    continue
                try:
                    result = await tools.call(name, **args)
                    tool_outputs.append(
                        f"<tool {name} ok={result.ok}>\n{result.to_text()[:4000]}\n</tool>"
                    )
                except Exception as e:
                    tool_outputs.append(f"<tool {name} error>{e}</tool>")

            messages.append(LLMMessage(role="assistant", content=reply))
            messages.append(
                LLMMessage(
                    role="user",
                    content="Tool results:\n\n" + "\n\n".join(tool_outputs)
                    + "\n\nContinue. If you have the final answer for the user, write it as plain text "
                      "with no tool-call block.",
                )
            )

        return "[max tool-rounds reached without a final answer]"

    def _build_tool_system_prompt(self, tools: "ToolRegistry") -> str:
        tool_list = []
        for t in tools.all():
            tool_list.append(
                f"- {t.name}: {t.description}\n  params: {json.dumps(t.parameters)}"
            )
        catalog = "\n".join(tool_list)
        return (
            self.system_prompt
            + "\n\n"
            + "You have access to the following tools:\n"
            + catalog
            + "\n\n"
            + "To call a tool, output a fenced JSON block like:\n"
            + "```tool\n"
            + '{"tool": "<name>", "args": {"<param>": "<value>"}}\n'
            + "```\n"
            + "You may emit multiple tool blocks in one reply; they will run in order.\n"
            + "When you're done with tools and ready to answer the user, write your final reply "
            + "as plain text with NO ```tool``` block."
        )

    @abstractmethod
    def __init__(self) -> None: ...


# --------------- tool-call parsing ---------------

import re

_TOOL_BLOCK_RE = re.compile(r"```tool\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_tool_calls(text: str) -> List[Dict[str, Any]]:
    calls: List[Dict[str, Any]] = []
    for m in _TOOL_BLOCK_RE.finditer(text):
        try:
            obj = json.loads(m.group(1))
            if isinstance(obj, dict) and "tool" in obj:
                calls.append(obj)
        except json.JSONDecodeError:
            continue
    return calls
