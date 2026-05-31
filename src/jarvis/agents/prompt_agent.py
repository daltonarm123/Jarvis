"""Prompt Jarvis — review video creative direction, prompts, and hook quality."""

from __future__ import annotations

from typing import List

from jarvis.agents.base_agent import BaseAgent, Capability


class PromptAgent(BaseAgent):
    name = "prompt"
    description = "Review short-form video creative direction, hooks, prompts, and quality checks."
    provider = "openai"
    model = "gpt-4o-mini"
    system_prompt = (
        "You are Prompt Jarvis. Your job is to review short-form video concepts, "
        "hooks, scripts, descriptions, and creative prompts. Make sure the creative "
        "direction is strong, on-brand, and optimized for virality. When asked, "
        "provide improved hooks, better prompt wording, and practical feedback for "
        "faceless video content. Keep responses concise and action-oriented."
    )

    def __init__(self) -> None:
        pass

    @classmethod
    def capabilities(cls) -> List[Capability]:
        return [
            Capability(
                "prompt_review",
                "Review and improve video prompts, hooks, scripts, and creative direction.",
                ["prompt", "review", "hook", "script", "creative direction",
                 "storyboard", "feedback", "improve", "polish", "rewrite", "refine"],
            ),
            Capability(
                "creative_quality",
                "Ensure creative assets are strong, concise, and engaging for short-form video.",
                ["quality", "clarity", "attention", "engagement", "strong hook",
                 "audience", "tone", "flow"],
            ),
        ]
