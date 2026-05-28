"""Router: decides which specialist handles a given task.

Two strategies, in order of preference:
  1. LLM classifier — cheap model picks the best agent given the task
     and the agent registry. Fast, accurate, costs ~$0.0001/turn.
  2. Keyword fallback — tally capability keyword hits. Works with no
     API keys and as a sanity check when the LLM picks something weird.
"""

from __future__ import annotations

import json
import re
from typing import List, Optional

from jarvis.agents import BaseAgent
from jarvis.llm import LLMMessage, get_provider


ROUTER_SYSTEM = """You are the Jarvis router. Given a user request and a list of specialist agents (each with capabilities), pick the SINGLE best agent to handle it. Reply with ONLY a JSON object:
{"agent": "<agent_name>", "reason": "<one short sentence>"}
Do not wrap in markdown. Do not add commentary."""


class JarvisRouter:
    def __init__(self, agents: List[BaseAgent], classifier_provider: str = "openai",
                 classifier_model: str = "gpt-4o-mini") -> None:
        self.agents = {a.name: a for a in agents}
        self.classifier_provider = classifier_provider
        self.classifier_model = classifier_model

    # ---------- public API ----------

    async def route(self, user_input: str) -> BaseAgent:
        agent_name = await self._llm_pick(user_input)
        if agent_name and agent_name in self.agents:
            return self.agents[agent_name]
        return self._keyword_pick(user_input)

    # ---------- LLM strategy ----------

    async def _llm_pick(self, user_input: str) -> Optional[str]:
        try:
            provider = get_provider(self.classifier_provider)
            if not provider.is_configured():
                return None
        except KeyError:
            return None

        catalog = self._catalog()
        prompt = (
            f"Specialist agents:\n{catalog}\n\n"
            f"User request: {user_input!r}\n\n"
            "Which agent should handle this?"
        )
        try:
            resp = await provider.complete(
                [LLMMessage(role="user", content=prompt)],
                model=self.classifier_model,
                system=ROUTER_SYSTEM,
                max_tokens=120,
                temperature=0.0,
            )
            data = self._extract_json(resp.content)
            if isinstance(data, dict) and isinstance(data.get("agent"), str):
                return data["agent"].strip().lower()
        except Exception:
            return None
        return None

    def _catalog(self) -> str:
        lines = []
        for a in self.agents.values():
            caps = "; ".join(c.name for c in type(a).capabilities()) or "(none)"
            lines.append(f"- {a.name}: {a.description} | capabilities: {caps}")
        return "\n".join(lines)

    @staticmethod
    def _extract_json(text: str):
        # Tolerate code fences just in case.
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None

    # ---------- keyword fallback ----------

    def _keyword_pick(self, user_input: str) -> BaseAgent:
        text = user_input.lower()
        scores: dict[str, int] = {name: 0 for name in self.agents}
        for name, agent in self.agents.items():
            for cap in type(agent).capabilities():
                for kw in cap.keywords:
                    # crude word-boundary-ish match
                    if re.search(rf"\b{re.escape(kw.lower())}\b", text):
                        scores[name] += 1
        # Default to personal if nothing matched.
        best = max(scores, key=lambda n: scores[n])
        if scores[best] == 0:
            return self.agents.get("personal") or next(iter(self.agents.values()))
        return self.agents[best]
