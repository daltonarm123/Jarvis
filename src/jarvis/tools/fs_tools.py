"""File system tools, scoped to a workspace directory.

Agents can NEVER read/write outside `workspace_root`. This is enforced
by resolving the requested path and checking it's a descendant.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from .base import Tool, ToolResult, ToolError


class WorkspaceScoped:
    """Mixin: turns a user-supplied relative path into a safe absolute path."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, rel: str) -> Path:
        if not rel or rel.strip() in (".", ""):
            return self.workspace_root
        candidate = (self.workspace_root / rel).resolve()
        try:
            candidate.relative_to(self.workspace_root)
        except ValueError:
            raise ToolError(
                f"Path {rel!r} escapes the workspace ({self.workspace_root})"
            )
        return candidate


class ReadFileTool(WorkspaceScoped, Tool):
    name = "read_file"
    description = "Read a UTF-8 text file from the agent workspace."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path inside workspace"},
            "max_bytes": {"type": "integer", "default": 200_000},
        },
        "required": ["path"],
    }

    async def run(self, path: str, max_bytes: int = 200_000) -> ToolResult:
        try:
            p = self._safe_path(path)
        except ToolError as e:
            return ToolResult(ok=False, error=str(e))
        if not p.exists():
            return ToolResult(ok=False, error=f"Not found: {path}")
        if not p.is_file():
            return ToolResult(ok=False, error=f"Not a file: {path}")
        try:
            data = p.read_bytes()[: int(max_bytes)]
            return ToolResult(
                ok=True,
                output=data.decode("utf-8", errors="replace"),
                meta={"size": p.stat().st_size, "truncated": p.stat().st_size > max_bytes},
            )
        except Exception as e:
            return ToolResult(ok=False, error=str(e))


class WriteFileTool(WorkspaceScoped, Tool):
    name = "write_file"
    description = "Create or overwrite a UTF-8 text file in the agent workspace."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
            "append": {"type": "boolean", "default": False},
        },
        "required": ["path", "content"],
    }

    async def run(self, path: str, content: str, append: bool = False) -> ToolResult:
        try:
            p = self._safe_path(path)
        except ToolError as e:
            return ToolResult(ok=False, error=str(e))
        p.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        try:
            with p.open(mode, encoding="utf-8") as f:
                f.write(content)
            return ToolResult(ok=True, output=f"Wrote {len(content)} chars to {path}",
                              meta={"path": str(p), "bytes": len(content.encode())})
        except Exception as e:
            return ToolResult(ok=False, error=str(e))


class ListDirTool(WorkspaceScoped, Tool):
    name = "list_dir"
    description = "List files in a workspace directory."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "default": "."},
            "recursive": {"type": "boolean", "default": False},
        },
    }

    async def run(self, path: str = ".", recursive: bool = False) -> ToolResult:
        try:
            p = self._safe_path(path)
        except ToolError as e:
            return ToolResult(ok=False, error=str(e))
        if not p.exists():
            return ToolResult(ok=False, error=f"Not found: {path}")
        if not p.is_dir():
            return ToolResult(ok=False, error=f"Not a directory: {path}")
        entries = []
        if recursive:
            for root, dirs, files in os.walk(p):
                # skip hidden dirs (.git, .venv, …)
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for name in files:
                    if name.startswith("."):
                        continue
                    full = Path(root) / name
                    entries.append(str(full.relative_to(self.workspace_root)))
        else:
            for child in sorted(p.iterdir()):
                if child.name.startswith("."):
                    continue
                tag = "d" if child.is_dir() else "f"
                entries.append(f"{tag} {child.relative_to(self.workspace_root)}")
        return ToolResult(ok=True, output="\n".join(entries) or "(empty)",
                          meta={"count": len(entries)})
