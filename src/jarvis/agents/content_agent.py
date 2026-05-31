"""Content Jarvis — short-form video ideas, scripts, hooks, and creator assets."""

from __future__ import annotations

from typing import List

from jarvis.agents.base_agent import BaseAgent, Capability


class ContentAgent(BaseAgent):
    name = "content"
    description = "Short-form content strategy: viral hooks, captions, scripts, and creator workflows."
    provider = "openai"
    model = "gpt-4o-mini"
    system_prompt = (
        "You are Content Jarvis. You create short-form video ideas, hooks, captions, and storyboards "
        "that are optimized for virality and fast engagement. Focus on practical formats, clear "
        "opening hooks, call-to-action ideas, and quick creative angles for TikTok, Reels, Shorts, "
        "and similar platforms. Present results as a set of ideas and execution-ready notes."
    )

    def __init__(self) -> None:
        pass

    @classmethod
    def capabilities(cls) -> List[Capability]:
        return [
            Capability(
                "short_form",
                "Create short-form video concepts, hooks, captions, and scripts.",
                ["short-form", "tiktok", "reels", "shorts", "hook", "viral", "video idea",
                 "caption", "script", "storyboard", "content idea"],
            ),
            Capability(
                "creator_assets",
                "Design creator-facing outputs like thumbnails, titles, descriptions, and CTAs.",
                ["title", "thumbnail", "caption", "headline", "video", "content"],
            ),
        ]
