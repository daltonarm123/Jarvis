"""Operations Jarvis — process design, automation, and execution workflows."""

from __future__ import annotations

from typing import List

from jarvis.agents.base_agent import BaseAgent, Capability


class OperationsAgent(BaseAgent):
    name = "operations"
    description = "Build SOPs, automation workflows, outsourcing plans, and operational systems."
    provider = "openai"
    model = "gpt-4o-mini"
    system_prompt = (
        "You are Operations Jarvis. You design repeatable systems that let Dalton scale his "
        "social publishing business with minimal hands-on work. Create clear operating "
        "procedures, automation checklists, task delegation plans, and quality-control steps. "
        "Focus on reliable execution and reducing manual overhead."
    )

    def __init__(self) -> None:
        pass

    @classmethod
    def capabilities(cls) -> List[Capability]:
        return [
            Capability(
                "processes",
                "Design SOPs, automation workflows, and quality systems.",
                ["process", "workflow", "system", "operations", "automation", "sop",
                 "delegate", "quality", "checklist", "scaling"],
            ),
            Capability(
                "execution",
                "Plan execution systems for content publishing and team coordination.",
                ["execution", "deployment", "coordination", "handoff", "launch",
                 "procedure", "system execution", "publish workflow"],
            ),
        ]
