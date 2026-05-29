"""Monetization Jarvis — revenue strategy, offers, and creator economy planning."""

from __future__ import annotations

from typing import List

from jarvis.agents.base_agent import BaseAgent, Capability


class MonetizationAgent(BaseAgent):
    name = "monetization"
    description = "Design revenue streams, affiliate funnels, sponsorship offers, and creator products."
    provider = "openai"
    model = "gpt-4o-mini"
    system_prompt = (
        "You are Monetization Jarvis. Your role is to help Dalton build profitable creator
"
        "business models around faceless short-form videos. Suggest ad, affiliate, product,
"
        "and service-based revenue strategies. Prioritize fast-moving ideas, scalable
"
        "offerings, and low-friction execution paths with clear profit potential."
    )

    def __init__(self) -> None:
        pass

    @classmethod
    def capabilities(cls) -> List[Capability]:
        return [
            Capability(
                "revenue",
                "Recommend monetization tactics, affiliate funnels, ad strategies, and products.",
                ["monetize", "revenue", "profit", "affiliate", "sponsorship", "ad", "offer",
                 "digital product", "course", "service", "subscription"],
            ),
            Capability(
                "business_model",
                "Create scalable business models for short-form creator content.",
                ["business", "model", "strategy", "scale", "income", "profit", "margins"],
            ),
        ]
