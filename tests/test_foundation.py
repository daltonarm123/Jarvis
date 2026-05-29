"""Smoke tests that work without any API keys."""

import asyncio
import os
import tempfile

import pytest

from jarvis.agents import (
    ALL_AGENTS,
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
)
from jarvis.core.router import JarvisRouter
from jarvis.memory import MemoryStore


def test_all_agents_instantiate():
    for cls in ALL_AGENTS:
        a = cls()
        assert a.name
        assert a.description
        assert a.provider
        assert a.model
        assert cls.capabilities() != []  # every agent declares something


def test_keyword_router_dev():
    agents = [cls() for cls in ALL_AGENTS]
    router = JarvisRouter(agents)
    a = router._keyword_pick("Can you refactor this Python function to be cleaner?")
    assert a.name == "dev"


def test_keyword_router_server():
    agents = [cls() for cls in ALL_AGENTS]
    router = JarvisRouter(agents)
    a = router._keyword_pick("My QB-Core garage script isn't working in Bloodmark RP")
    assert a.name == "server"


def test_keyword_router_discord():
    agents = [cls() for cls in ALL_AGENTS]
    router = JarvisRouter(agents)
    a = router._keyword_pick("Add a slash command to the wheel-spin discord bot")
    assert a.name == "discord"


def test_keyword_router_growth():
    agents = [cls() for cls in ALL_AGENTS]
    router = JarvisRouter(agents)
    a = router._keyword_pick("Research trending side hustles and monetization methods for short-form content")
    assert a.name == "growth"


def test_keyword_router_content():
    agents = [cls() for cls in ALL_AGENTS]
    router = JarvisRouter(agents)
    a = router._keyword_pick("Help me write a viral TikTok hook and video script")
    assert a.name == "content"


def test_keyword_router_research():
    agents = [cls() for cls in ALL_AGENTS]
    router = JarvisRouter(agents)
    a = router._keyword_pick("What is trending now in creator economy and short-form videos?")
    assert a.name == "research"


def test_keyword_router_social():
    agents = [cls() for cls in ALL_AGENTS]
    router = JarvisRouter(agents)
    a = router._keyword_pick("Create a new TikTok account and schedule a short video post")
    assert a.name == "social"


def test_keyword_router_analytics():
    agents = [cls() for cls in ALL_AGENTS]
    router = JarvisRouter(agents)
    a = router._keyword_pick("Analyze our video performance and tell me which posts are converting best")
    assert a.name == "analytics"


def test_keyword_router_monetization():
    agents = [cls() for cls in ALL_AGENTS]
    router = JarvisRouter(agents)
    a = router._keyword_pick("How can we monetize our creator videos with sponsors or products?")
    assert a.name == "monetization"


def test_keyword_router_operations():
    agents = [cls() for cls in ALL_AGENTS]
    router = JarvisRouter(agents)
    a = router._keyword_pick("Create a process for publishing daily faceless videos and outsourcing editing")
    assert a.name == "operations"


def test_keyword_router_personal_fallback():
    agents = [cls() for cls in ALL_AGENTS]
    router = JarvisRouter(agents)
    a = router._keyword_pick("hey what's up")
    assert a.name == "personal"  # default fallback


def test_memory_store():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        m = MemoryStore(path)
        m.add_message("s1", "user", "hi", agent="personal")
        m.add_message("s1", "assistant", "hello", agent="personal")
        msgs = m.recent_messages("s1")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"

        m.set_fact("name", "dalton")
        assert m.get_fact("name") == "dalton"
        assert m.get_fact("missing", "default") == "default"

        m.set_agent_state("dev", {"last_repo": "Jarvis"})
        assert m.get_agent_state("dev")["last_repo"] == "Jarvis"
        m.close()
    finally:
        os.unlink(path)


@pytest.mark.asyncio
async def test_router_falls_back_to_keywords_without_keys(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    agents = [cls() for cls in ALL_AGENTS]
    router = JarvisRouter(agents)
    a = await router.route("write me a python script")
    assert a.name == "dev"


@pytest.mark.asyncio
async def test_core_handles_help_without_keys(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from jarvis.core.jarvis_core import JarvisCore
    j = JarvisCore()
    out = await j.handle("/help")
    assert "/agents" in out
    out2 = await j.handle("/agents")
    assert "dev" in out2 and "server" in out2
    out3 = await j.handle("/status")
    assert "Session" in out3
