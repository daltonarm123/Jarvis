"""Growth Jarvis — trend research and monetization opportunity discovery."""

from __future__ import annotations

from typing import List

from jarvis.agents.base_agent import BaseAgent, Capability


class GrowthAgent(BaseAgent):
    name = "growth"
    description = "Trend research, monetization opportunities, niches, and business model ideas."
    provider = "openai"
    model = "gpt-4o-mini"
    system_prompt = (
        "You are Growth Jarvis. Your job is to uncover high-potential money-making ideas,
"
        "platform trends, niches, traffic channels, and business models that Dalton can pursue.
"
        "Focus on research-backed opportunities, explain why each idea matters, and highlight
"
        "what is currently trending in short-form content, creator economy, and digital products.
"
        "Keep your output concise and clearly organized so the manager can assign follow-up work."
    )

    def __init__(self) -> None:
        pass

    @classmethod
    def capabilities(cls) -> List[Capability]:
        return [
            Capability(
                "trend_research",
                "Research trending niches, monetization methods, and creator economy opportunities.",
                ["trend", "trending", "niche", "monetization", "opportunity", "side hustle",
                 "make money", "business model", "creator economy"],
            ),
            Capability(
                "platform_strategy",
                "Recommend platforms, channels, and formats for growth and income.",
                ["tiktok", "youtube", "instagram", "shorts", "reels", "platform", "algorithm"],
            ),
        ]
