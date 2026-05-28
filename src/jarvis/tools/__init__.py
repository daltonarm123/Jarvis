"""Tool system for Jarvis agents.

Tools are how agents *do* things, not just chat. Each tool:
  - declares a JSON schema (LLM function-calling compatible)
  - has an async `run()` that returns a `ToolResult`
  - is sandboxed and idempotent where possible

Built-in tools:
  - read_file / write_file / list_dir   (scoped to workspace)
  - shell                                (allowlist + timeout)
  - web_fetch                            (URL → markdown text)
  - http_get                             (raw GET with timeout)

Adding a new tool: subclass `Tool`, implement `run()`, append to
`builtin_tools()`.
"""

from .base import Tool, ToolResult, ToolError, ToolRegistry
from .builtins import builtin_tools

__all__ = [
    "Tool",
    "ToolResult",
    "ToolError",
    "ToolRegistry",
    "builtin_tools",
]
