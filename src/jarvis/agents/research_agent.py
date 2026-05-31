"""Research Jarvis — trending topics, market signals, and content opportunities."""

from __future__ import annotations

from typing import List

from jarvis.agents.base_agent import BaseAgent, Capability


class ResearchAgent(BaseAgent):
    name = "research"
    description = "Trend research: discover viral topics, content opportunities, and business signals."
    provider = "openai"
    model = "gpt-4o-mini"
    system_prompt = (
        "You are Research Jarvis. Your job is to discover what is trending, what audiences are "
        "responding to, and where the next short-form content opportunities exist. "
        "Provide concise market signals, platform trends, and content angles. When you identify "
        "strong ideas, suggest them as recommendations for the social automation team, but do not "
        "publish or execute anything without Jarvis manager approval."
    )

    def __init__(self) -> None:
        pass

    @classmethod
    def capabilities(cls) -> List[Capability]:
        return [
            Capability(
                "trend_research",
                "Discover trending topics, viral ideas, and content opportunity signals.",
                ["trend", "trending", "viral", "buzz", "topic", "niche",
                 "audience interest", "search signal", "content theme"],
            ),
            Capability(
                "market_insight",
                "Identify audience needs, market signals, and content opportunity themes.",
                ["opportunity", "signal", "market", "theme", "idea",
                 "content angle", "audience", "creator economy"],
            ),
        ]
