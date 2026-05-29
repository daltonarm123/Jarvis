"""Manager Jarvis — CEO-facing head agent for daily briefings and task planning."""

from __future__ import annotations

from typing import List

from jarvis.agents.base_agent import BaseAgent, Capability


class ManagerAgent(BaseAgent):
    name = "manager"
    description = "CEO-facing head agent: daily briefings, progress summaries, and team coordination."
    provider = "openai"
    model = "gpt-4o-mini"
    system_prompt = (
        "You are Manager Jarvis. You report directly to Dalton as the head AI manager.
"
        "Your job is to summarize progress, produce daily briefings, and assign clear
"
        "actionable priorities for the specialist agents. Present your answers in a
"
        "professional, concise format suitable for a daily standup summary."
    )

    def __init__(self) -> None:
        pass

    @classmethod
    def capabilities(cls) -> List[Capability]:
        return [
            Capability(
                "planning",
                "Create daily briefings, priorities, and action plans for the agent team.",
                ["daily", "briefing", "summary", "plan", "standup", "today", "priority"],
            ),
        ]
