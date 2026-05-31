"""Smoke tests that work without any API keys."""

import asyncio
import os
import tempfile

import pytest

from jarvis.agents import (
    ALL_AGENTS,
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
    TaskContext,
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


def test_keyword_router_prompt():
    agents = [cls() for cls in ALL_AGENTS]
    router = JarvisRouter(agents)
    a = router._keyword_pick("Review this video prompt and make sure the hook is strong")
    assert a.name == "prompt"


def test_keyword_router_growth():
    agents = [cls() for cls in ALL_AGENTS]
    router = JarvisRouter(agents)
    a = router._keyword_pick("Recommend a platform growth strategy and audience scaling plan for short-form video channels")
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


def test_platform_registry_available_connectors():
    from jarvis.platforms.registry import available_platforms, get_connector

    platforms = available_platforms()
    assert set(platforms) == {"facebook", "instagram", "tiktok", "youtube"}
    assert get_connector("tiktok").name == "tiktok"
    assert get_connector("instagram").name == "meta"


@pytest.mark.parametrize(
    "platform,alias",
    [
        ("tiktok", "tiktok_test"),
        ("instagram", "insta_test"),
        ("facebook", "fb_page"),
        ("youtube", "yt_channel"),
    ],
)
@pytest.mark.asyncio
async def test_social_agent_can_create_accounts_for_all_platforms(tmp_path, platform, alias):
    memory = MemoryStore(str(tmp_path / "jarvis.db"))
    agent = SocialAgent()
    ctx = TaskContext(
        session_id="s1",
        user_input=f"create account for {platform} as {alias}",
        history=[],
        memory=memory,
    )

    out = await agent.handle(ctx)
    assert "Account alias" in out
    state = memory.get_agent_state("social")
    assert len(state.get("accounts", [])) == 1
    assert state["accounts"][0]["platform"] == platform
    assert state["accounts"][0]["alias"] == alias
    assert state["accounts"][0]["status"] in {"pending", "active"}
    assert "credentials" not in state["accounts"][0] or state["accounts"][0]["has_credentials"] is False
    memory.close()


@pytest.mark.asyncio
async def test_social_agent_stores_credentials_for_existing_account(tmp_path):
    memory = MemoryStore(str(tmp_path / "jarvis.db"))
    agent = SocialAgent()
    create_ctx = TaskContext(
        session_id="s2",
        user_input="create account for youtube as yt_test",
        history=[],
        memory=memory,
    )
    await agent.handle(create_ctx)

    update_ctx = TaskContext(
        session_id="s2",
        user_input=(
            "add credentials for youtube yt_test "
            "access_token=ABC123"
        ),
        history=[],
        memory=memory,
    )
    out = await agent.handle(update_ctx)
    assert "Credentials for youtube account 'yt_test' have been securely stored" in out

    state = memory.get_agent_state("social")
    assert state["accounts"][0]["has_credentials"] is True
    memory.close()


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
    assert "dev" in out2 and "prompt" in out2
    out3 = await j.handle("/status")
    assert "Session" in out3

@pytest.mark.asyncio
async def test_core_account_add_and_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from jarvis.core.jarvis_core import JarvisCore

    j = JarvisCore()
    out = await j.handle("/account add platform=instagram alias=insta_test")
    assert "Account alias: insta_test" in out
    out2 = await j.handle("/accounts")
    assert "insta_test (instagram)" in out2
    out3 = await j.handle("/account instagram")
    assert "Accounts for instagram:" in out3

    out4 = await j.handle(
        "/account credentials platform=instagram alias=insta_test access_token=ABC123 instagram_business_account_id=98765"
    )
    assert "securely stored" in out4.lower()
    state = j.memory.get_agent_state("social")
    assert state["accounts"][0]["has_credentials"] is True

@pytest.mark.asyncio
async def test_core_profit_and_wake_phrase(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from jarvis.core.jarvis_core import JarvisCore

    j = JarvisCore()
    j.memory.set_fact("profit_q2", 1200)
    j.memory.set_fact("revenue_tiktok", "$3,500")
    j.memory.set_fact("last_daily_briefing", "This is today's manager briefing.")
    j.task_monitor.sync_tasks({"social": "Post 3 videos today."})

    profit_out = await j.handle("/profit")
    assert "profit_q2" in profit_out
    assert "revenue_tiktok" in profit_out
    assert "Total recognized numeric profit/revenue" in profit_out

    wake_out = await j.handle("hello jarvis tell me whats going on today")
    assert "Daily briefing" in wake_out
    assert "Current work plan for the team" in wake_out
    assert "Profit summary" in wake_out

@pytest.mark.asyncio
async def test_core_tasks_and_general_ask(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from jarvis.core.jarvis_core import JarvisCore

    j = JarvisCore()
    out = await j.handle("/tasks")
    assert "No active tasks" in out
    out2 = await j.handle("/ask what is Jarvis?")
    assert "Personal agent not available" not in out2

@pytest.mark.asyncio
async def test_core_health_and_escalation(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from jarvis.core.jarvis_core import JarvisCore

    j = JarvisCore()
    health_out = await j.handle("/health")
    assert "All systems nominal" in health_out or "No issues detected" in health_out
    escalate_out = await j.handle("/escalate")
    assert "No critical issues to escalate." in escalate_out
