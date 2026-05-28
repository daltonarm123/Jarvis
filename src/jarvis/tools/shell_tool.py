"""Shell tool. Sandboxed via:
  - command allowlist (configurable, conservative defaults)
  - cwd restricted to a workspace dir
  - hard timeout
  - no shell metacharacters by default (use raw_shell=True for &&/|, with caution)
"""

from __future__ import annotations

import asyncio
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .base import Tool, ToolResult, ToolError


# Conservative default. Add more via ShellTool(allowlist=[...]) when needed.
DEFAULT_ALLOWLIST: Set[str] = {
    # navigation / inspection
    "ls", "pwd", "echo", "cat", "head", "tail", "wc", "grep", "find", "tree",
    "file", "stat",
    # text ops
    "cut", "sort", "uniq", "awk", "sed",
    # python / node / git (read-mostly)
    "python3", "python", "node", "npm", "git",
    # ffmpeg/ffprobe (we'll need these for the video pipeline)
    "ffmpeg", "ffprobe",
    # network probes
    "curl", "wget",
    # archive
    "tar", "zip", "unzip", "gunzip", "gzip",
    # gh CLI
    "gh",
}

# Commands we never allow even if user adds them.
HARD_DENY = {"rm", "rmdir", "shutdown", "reboot", "mkfs", "dd", "shred",
             "passwd", "useradd", "userdel", "chown", "chmod", "sudo", "su"}


class ShellTool(Tool):
    name = "shell"
    description = (
        "Run a shell command in the agent workspace. "
        "Defaults to a strict allowlist; commands like rm/sudo are denied. "
        "Returns stdout/stderr and exit code."
    )
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Command line to execute"},
            "timeout": {"type": "number", "default": 30, "description": "Max seconds"},
            "raw_shell": {
                "type": "boolean",
                "default": False,
                "description": "Allow shell metacharacters (|, &&, etc). Use sparingly.",
            },
        },
        "required": ["command"],
    }

    def __init__(
        self,
        workspace_root: str | Path,
        allowlist: Optional[List[str]] = None,
        max_timeout: float = 120.0,
    ) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.allowlist: Set[str] = set(allowlist) if allowlist is not None else set(DEFAULT_ALLOWLIST)
        self.max_timeout = float(max_timeout)

    def _check_program(self, prog: str) -> None:
        base = Path(prog).name.lower()
        if base in HARD_DENY:
            raise ToolError(f"Command not allowed: {base}")
        if base not in self.allowlist:
            raise ToolError(
                f"Command {base!r} not in allowlist. "
                f"Available: {sorted(self.allowlist)}"
            )

    async def run(
        self,
        command: str,
        timeout: float = 30.0,
        raw_shell: bool = False,
    ) -> ToolResult:
        timeout = min(float(timeout), self.max_timeout)

        if raw_shell:
            # Even in raw mode, scan for hard-denied programs.
            for token in command.split():
                base = Path(token).name.lower().rstrip(";|&")
                if base in HARD_DENY:
                    return ToolResult(ok=False, error=f"Command contains denied program: {base}")
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=str(self.workspace_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        else:
            try:
                argv = shlex.split(command)
            except ValueError as e:
                return ToolResult(ok=False, error=f"Parse error: {e}")
            if not argv:
                return ToolResult(ok=False, error="Empty command")
            try:
                self._check_program(argv[0])
            except ToolError as e:
                return ToolResult(ok=False, error=str(e))
            proc = await asyncio.create_subprocess_exec(
                *argv,
                cwd=str(self.workspace_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return ToolResult(ok=False, error=f"Timeout after {timeout}s",
                              meta={"timeout": timeout})

        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")
        return ToolResult(
            ok=proc.returncode == 0,
            output=out if proc.returncode == 0 else f"{out}\n--- stderr ---\n{err}",
            error=None if proc.returncode == 0 else f"exit={proc.returncode}",
            meta={"returncode": proc.returncode, "stdout_len": len(out), "stderr_len": len(err)},
        )
