"""Analytics Jarvis — performance tracking, metrics analysis, and growth optimization."""

from __future__ import annotations

from typing import List

from jarvis.agents.base_agent import BaseAgent, Capability


class AnalyticsAgent(BaseAgent):
    name = "analytics"
    description = "Analyze content performance, audience growth, and campaign metrics."
    provider = "openai"
    model = "gpt-4o-mini"
    system_prompt = (
        "You are Analytics Jarvis. You help Dalton understand what is working and why. "
        "Use available data, metrics, and performance signals to identify the best paths "
        "for growth, retention, and algorithmic optimization. Give concise KPI-driven "
        "recommendations and explain trade-offs clearly."
    )

    def __init__(self) -> None:
        pass

    @classmethod
    def capabilities(cls) -> List[Capability]:
        return [
            Capability(
                "performance",
                "Analyze content performance, engagement, and conversion metrics.",
                ["metrics", "analytics", "performance", "kpi", "engagement",
                 "conversion", "watch time", "retention", "click-through", "analysis"],
            ),
            Capability(
                "optimization",
                "Recommend optimizations for reach, watch time, and audience retention.",
                ["optimize", "improve", "increase", "watch time", "retention",
                 "performance", "efficiency", "optimize reach"],
            ),
        ]
