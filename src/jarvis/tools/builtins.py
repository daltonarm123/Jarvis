"""Convenience: build a registry pre-loaded with all built-in tools."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from .base import Tool, ToolRegistry
from .fs_tools import ReadFileTool, WriteFileTool, ListDirTool
from .shell_tool import ShellTool
from .web_tools import HttpGetTool, WebFetchTool


def builtin_tools(workspace_root: Optional[str | Path] = None,
                  shell_allowlist: Optional[List[str]] = None) -> ToolRegistry:
    """Return a registry with every standard tool wired up."""
    workspace_root = workspace_root or os.getenv("AGENT_WORKSPACE", "./agent_workspace")
    return ToolRegistry([
        ReadFileTool(workspace_root),
        WriteFileTool(workspace_root),
        ListDirTool(workspace_root),
        ShellTool(workspace_root, allowlist=shell_allowlist),
        HttpGetTool(),
        WebFetchTool(),
    ])
