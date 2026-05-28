"""Jarvis orchestrator.

Owns:
  - the agent registry
  - the router
  - the memory store
  - the conversation loop

Front-ends (CLI, Discord, voice) call `JarvisCore.handle(user_input)` —
that's the single integration point.
"""

from __future__ import annotations

import os
import uuid
from typing import List, Optional

from jarvis.agents import ALL_AGENTS, BaseAgent, TaskContext
from jarvis.core.router import JarvisRouter
from jarvis.memory import MemoryStore


class JarvisCore:
    def __init__(self, session_id: Optional[str] = None) -> None:
        self.session_id = session_id or f"cli-{uuid.uuid4().hex[:8]}"
        self.memory = MemoryStore(os.getenv("DATA_DIR", "./data") + "/jarvis.db")
        self.agents: List[BaseAgent] = [cls() for cls in ALL_AGENTS]
        self.router = JarvisRouter(self.agents)
        self.autonomous_mode = os.getenv("JARVIS_MODE", "interactive") == "autonomous"

    # ---------- main entry point ----------

    async def handle(self, user_input: str) -> str:
        text = user_input.strip()
        if not text:
            return ""

        # Slash-style commands bypass the router.
        if text.startswith("/"):
            return await self._handle_command(text[1:])

        # Direct address: "@dev refactor this" → forces routing.
        forced = self._extract_at_mention(text)
        if forced:
            agent_name, payload = forced
            agent = next((a for a in self.agents if a.name == agent_name), None)
            if agent is None:
                return f"No agent named '{agent_name}'. Try /agents."
            return await self._dispatch(agent, payload)

        agent = await self.router.route(text)
        return await self._dispatch(agent, text)

    # ---------- internals ----------

    async def _dispatch(self, agent: BaseAgent, user_input: str) -> str:
        self.memory.add_message(self.session_id, "user", user_input, agent=agent.name)
        history = self.memory.recent_messages(self.session_id, limit=20)
        ctx = TaskContext(
            session_id=self.session_id,
            user_input=user_input,
            history=history,
            memory=self.memory,
        )
        try:
            reply = await agent.handle(ctx)
        except Exception as e:  # don't crash the loop on agent errors
            reply = f"[{agent.name}] error: {e}"
        self.memory.add_message(self.session_id, "assistant", reply, agent=agent.name)
        return f"[{agent.name}] {reply}"

    async def _handle_command(self, cmd: str) -> str:
        parts = cmd.split(maxsplit=1)
        head = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""

        if head in ("help", "h", "?"):
            return self._help_text()
        if head == "agents":
            return self._agents_text()
        if head == "status":
            return self._status_text()
        if head == "remember":
            return self._cmd_remember(rest)
        if head == "facts":
            facts = self.memory.all_facts()
            if not facts:
                return "No facts stored."
            return "\n".join(f"- {k}: {v}" for k, v in facts.items())
        if head == "session":
            return f"Session: {self.session_id}"
        return f"Unknown command: /{head}. Try /help."

    def _cmd_remember(self, rest: str) -> str:
        if "=" not in rest:
            return "Usage: /remember key = value"
        key, value = (s.strip() for s in rest.split("=", 1))
        self.memory.set_fact(key, value)
        return f"Remembered: {key} = {value}"

    def _help_text(self) -> str:
        return (
            "Jarvis commands:\n"
            "  /help                   Show this help\n"
            "  /agents                 List specialist agents\n"
            "  /status                 Provider + agent status\n"
            "  /remember key = value   Store a fact\n"
            "  /facts                  Show all stored facts\n"
            "  /session                Show current session id\n"
            "  @<agent> <task>         Force route to a specific agent\n"
            "  <anything else>         Auto-routed by Jarvis"
        )

    def _agents_text(self) -> str:
        out = ["Specialist agents:"]
        for a in self.agents:
            out.append(f"  • {a.name:10s} ({a.provider}/{a.model})")
            out.append(f"    {a.description}")
        return "\n".join(out)

    def _status_text(self) -> str:
        from jarvis.llm import available_providers
        configured = available_providers(only_configured=True)
        all_p = available_providers()
        return (
            f"Session: {self.session_id}\n"
            f"Mode: {'autonomous' if self.autonomous_mode else 'interactive'}\n"
            f"Providers configured: {configured or 'NONE'}\n"
            f"Providers available:  {all_p}\n"
            f"Agents loaded: {len(self.agents)}"
        )

    @staticmethod
    def _extract_at_mention(text: str):
        if not text.startswith("@"):
            return None
        head, _, payload = text[1:].partition(" ")
        if not head or not payload:
            return None
        return head.lower(), payload.strip()

    # ---------- legacy CLI loop ----------

    async def run(self) -> None:
        from jarvis.communication.user_interface import UserInterface
        ui = UserInterface()
        print("Jarvis online. Type /help for commands. Ctrl-C or 'quit' to exit.\n")
        while True:
            try:
                user_input = await ui.get_input()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if user_input.strip().lower() in ("quit", "exit"):
                break
            if not user_input.strip():
                continue
            reply = await self.handle(user_input)
            await ui.send_output(reply)
        print("Shutting down Jarvis.")
        self.memory.close()
