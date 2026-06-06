import asyncio
import json
import os
from pathlib import Path

import pytest

from jarvis.agents import DevAgent, AppAgent, TaskContext
from jarvis.core.jarvis_core import JarvisCore


class DummyProvider:
    def __init__(self, content: str):
        self.name = "dummy"
        self._content = content

    def is_configured(self):
        return True

    async def complete(self, messages, model=None, system=None, max_tokens=1024, temperature=0.0):
        class R:
            def __init__(self, c):
                self.content = c

        return R(self._content)


@pytest.mark.asyncio
async def test_dev_agent_review_parses_json(monkeypatch, tmp_path):
    # Create a temporary file under the repo root to review
    repo_root = Path(__file__).resolve().parents[1]
    testfile = repo_root / "tmp_dev_review.txt"
    testfile.write_text("original content")

    # Prepare dummy LLM response with JSON block
    json_block = json.dumps({
        "summary": "Minor change",
        "patches": [
            {"path": str(testfile.relative_to(repo_root)), "content": "fixed content", "simple": True, "rationale": "fix typo"}
        ],
    })
    resp_text = "Found a small issue.\n\n" + json_block

    # Monkeypatch provider lookup to return the dummy provider
    monkeypatch.setattr("jarvis.llm.get_provider", lambda name: DummyProvider(resp_text))

    agent = DevAgent()
    ctx = TaskContext(session_id="s1", user_input=f"review file {testfile.relative_to(repo_root)}", history=[], memory=None)
    out = await agent.handle(ctx)

    assert "Suggested JSON" in out or "patches" in out
    # Clean up
    try:
        testfile.unlink()
    except Exception:
        pass


def test_apply_patch_skips_non_simple(tmp_path):
    j = JarvisCore()
    patches = {"patches": [{"path": "some/file.py", "content": "print(1)", "simple": False}]}
    patch_file = tmp_path / "patches.json"
    patch_file.write_text(json.dumps(patches))

    out = j._apply_patch(str(patch_file))
    assert "Skipped" in out
    assert "ALLOW_DEV_APPLY" in out
