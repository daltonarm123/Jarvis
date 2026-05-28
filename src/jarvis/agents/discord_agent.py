"""Discord Jarvis — bot dev, moderation, community management."""

from __future__ import annotations

from typing import List

from jarvis.agents.base_agent import BaseAgent, Capability


class DiscordAgent(BaseAgent):
    name = "discord"
    description = "Discord bot development, moderation, community automation."
    provider = "openai"
    model = "gpt-4o-mini"
    system_prompt = (
        "You are Discord Jarvis. You help Dalton build and maintain Discord bots\n"
        "(including the Wheel Spin bot and FiveM-integrated bots). You're fluent in\n"
        "discord.py, slash commands, role/permission systems, moderation, and webhooks.\n"
        "Keep replies practical and focused on shipping working bot code or commands."
    )

    def __init__(self) -> None:
        pass

    @classmethod
    def capabilities(cls) -> List[Capability]:
        return [
            Capability(
                "discord_bot",
                "Build / modify Discord bots, slash commands, role automation.",
                ["discord", "bot", "slash command", "wheel spin", "wheel-spin",
                 "moderation", "role", "embed", "webhook"],
            ),
        ]
