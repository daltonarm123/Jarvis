"""Tests for the tool system. No API keys required."""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from jarvis.tools import builtin_tools, ToolError
from jarvis.tools.base import Tool, ToolResult, ToolRegistry
from jarvis.tools.fs_tools import ReadFileTool, WriteFileTool, ListDirTool
from jarvis.tools.shell_tool import ShellTool


@pytest.mark.asyncio
async def test_workspace_scoping_blocks_escape(tmp_path):
    rt = ReadFileTool(tmp_path)
    # Try to escape via ../
    res = await rt.run(path="../etc/passwd")
    assert res.ok is False
    assert "escape" in (res.error or "").lower()


@pytest.mark.asyncio
async def test_write_then_read_roundtrip(tmp_path):
    wt = WriteFileTool(tmp_path)
    rt = ReadFileTool(tmp_path)
    res = await wt.run(path="hello.txt", content="hi there")
    assert res.ok
    res = await rt.run(path="hello.txt")
    assert res.ok and res.output == "hi there"


@pytest.mark.asyncio
async def test_list_dir(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("b")
    ld = ListDirTool(tmp_path)
    res = await ld.run(path=".")
    assert res.ok
    assert "a.txt" in res.output and "sub" in res.output
    res = await ld.run(path=".", recursive=True)
    assert "sub/b.txt" in res.output or "sub\\b.txt" in res.output  # path sep


@pytest.mark.asyncio
async def test_shell_allowlist_blocks_rm(tmp_path):
    sh = ShellTool(tmp_path)
    res = await sh.run(command="rm -rf /")
    assert res.ok is False
    assert "not allowed" in (res.error or "").lower() or "not in allowlist" in (res.error or "").lower()


@pytest.mark.asyncio
async def test_shell_runs_echo(tmp_path):
    sh = ShellTool(tmp_path)
    res = await sh.run(command="echo hello-jarvis")
    assert res.ok
    assert "hello-jarvis" in res.output


@pytest.mark.asyncio
async def test_shell_timeout(tmp_path):
    sh = ShellTool(tmp_path)
    # python sleeps 5s; we cap at 0.5s
    res = await sh.run(command="python3 -c 'import time; time.sleep(5)'", timeout=0.5)
    assert res.ok is False
    assert "timeout" in (res.error or "").lower()


@pytest.mark.asyncio
async def test_shell_denies_sudo_in_raw_mode(tmp_path):
    sh = ShellTool(tmp_path)
    res = await sh.run(command="sudo ls", raw_shell=True)
    assert res.ok is False


@pytest.mark.asyncio
async def test_registry_unknown_tool(tmp_path):
    reg = ToolRegistry()
    res = await reg.call("nonexistent")
    assert res.ok is False


def test_builtin_registry_has_all(tmp_path):
    reg = builtin_tools(tmp_path)
    names = set(reg.names())
    assert {"read_file", "write_file", "list_dir", "shell", "http_get", "web_fetch"}.issubset(names)


def test_tool_schemas_round_trip(tmp_path):
    reg = builtin_tools(tmp_path)
    openai = reg.openai_schemas()
    assert all(s["type"] == "function" for s in openai)
    anth = reg.anthropic_schemas()
    assert all("input_schema" in s for s in anth)
