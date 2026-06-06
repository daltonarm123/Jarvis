"""Jarvis specialist agents."""

from .base_agent import BaseAgent, Capability, TaskContext
from .dev_agent import DevAgent
from .prompt_agent import PromptAgent
from .personal_agent import PersonalAgent
from .growth_agent import GrowthAgent
from .content_agent import ContentAgent
from .social_agent import SocialAgent
from .research_agent import ResearchAgent
from .analytics_agent import AnalyticsAgent
from .monetization_agent import MonetizationAgent
from .operations_agent import OperationsAgent
from .video_editor_agent import VideoEditorAgent
from .email_agent import EmailAgent
from .app_agent import AppAgent

ALL_AGENTS = [
    DevAgent,
    PromptAgent,
    PersonalAgent,
    GrowthAgent,
    ContentAgent,
    ResearchAgent,
    SocialAgent,
    AnalyticsAgent,
    MonetizationAgent,
    OperationsAgent,
    VideoEditorAgent,
    EmailAgent,
    AppAgent,
]

__all__ = [
    "BaseAgent",
    "Capability",
    "TaskContext",
    "DevAgent",
    "PromptAgent",
    "PersonalAgent",
    "GrowthAgent",
    "ContentAgent",
    "ResearchAgent",
    "SocialAgent",
    "AnalyticsAgent",
    "MonetizationAgent",
    "OperationsAgent",
    "EmailAgent",
    "AppAgent",
    "ALL_AGENTS",
]
