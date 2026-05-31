"""Personal Jarvis — schedule, tasks, reminders, general assistance."""

from __future__ import annotations

from typing import List

from jarvis.agents.base_agent import BaseAgent, Capability


class PersonalAgent(BaseAgent):
    name = "personal"
    description = "Personal productivity: schedule, tasks, reminders, quick research."
    provider = "openai"
    model = "gpt-4o-mini"
    system_prompt = (
        "You are Personal Jarvis. You help Dalton stay organized: tasks, reminders,\n"
        "scheduling, quick lookups, summarization. Keep replies short and actionable.\n"
        "If asked something outside your scope, say so — the router will hand it to the right specialist."
    )

    def __init__(self) -> None:
        pass

    @classmethod
    def capabilities(cls) -> List[Capability]:
        return [
            Capability(
                "tasks",
                "Manage tasks, todos, reminders, calendar.",
                ["task", "todo", "to-do", "remind", "schedule", "calendar",
                 "deadline", "agenda"],
            ),
            Capability(
                "general",
                "General questions, summaries, quick research.",
                ["what is", "explain", "summarize", "tell me", "how do"],
            ),
        ]
