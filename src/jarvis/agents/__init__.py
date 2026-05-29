"""Jarvis specialist agents."""

from .base_agent import BaseAgent, Capability, TaskContext
from .dev_agent import DevAgent
from .server_agent import ServerAgent
from .discord_agent import DiscordAgent
from .personal_agent import PersonalAgent
from .growth_agent import GrowthAgent
from .content_agent import ContentAgent
from .social_agent import SocialAgent
from .research_agent import ResearchAgent
from .analytics_agent import AnalyticsAgent
from .monetization_agent import MonetizationAgent
from .operations_agent import OperationsAgent

ALL_AGENTS = [
    DevAgent,
    ServerAgent,
    DiscordAgent,
    PersonalAgent,
    GrowthAgent,
    ContentAgent,
    ResearchAgent,
    SocialAgent,
    AnalyticsAgent,
    MonetizationAgent,
    OperationsAgent,
]

__all__ = [
    "BaseAgent",
    "Capability",
    "TaskContext",
    "DevAgent",
    "ServerAgent",
    "DiscordAgent",
    "PersonalAgent",
    "GrowthAgent",
    "ContentAgent",
    "ResearchAgent",
    "SocialAgent",
    "AnalyticsAgent",
    "MonetizationAgent",
    "OperationsAgent",
    "ALL_AGENTS",
]
