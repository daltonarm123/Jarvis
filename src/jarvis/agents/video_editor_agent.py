"""Video Editor Jarvis — produce editing plans for short-form videos."""

from __future__ import annotations

from typing import List

from jarvis.agents.base_agent import BaseAgent, Capability


class VideoEditorAgent(BaseAgent):
    name = "video_editor"
    description = "Generate video editing plans, transitions, and post-production notes for short-form videos."
    provider = "openai"
    model = "gpt-4o-mini"
    system_prompt = (
        "You are Video Editor Jarvis. Your job is to design concise video editing plans, shot structure, transition timing, and production notes for short-form faceless videos. "
        "Recommend the best pacing, scene changes, text overlays, and style choices for virality. "
        "Keep the plan actionable for an editor or automation workflow."
    )

    def __init__(self) -> None:
        pass

    @classmethod
    def capabilities(cls) -> List[Capability]:
        return [
            Capability(
                "video_edit",
                "Produce video editing plans, transitions, and execution notes for short-form content.",
                ["edit", "video", "render", "trim", "cut", "transition", "timeline", "post-production", "overlay", "shot"],
            )
        ]
