"""Web tools: HTTP GET and a markdown-extraction fetch.

Lightweight by design — no heavy dependencies. Markdown extraction
uses a small HTML→text converter so we don't pull in BeautifulSoup
unless the agent actually needs it.
"""

from __future__ import annotations

import asyncio
import re
from html import unescape
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from .base import Tool, ToolResult


_DEFAULT_TIMEOUT = 15.0
_DEFAULT_UA = "JarvisBot/0.1 (+https://github.com/daltonarm123/Jarvis)"


def _strip_html(html: str, max_chars: int = 20_000) -> str:
    # remove script/style blocks
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.S | re.I)
    # block-level → newline
    html = re.sub(r"</?(p|div|br|li|h\d|tr|table|article|section)[^>]*>", "\n", html, flags=re.I)
    # everything else → strip
    text = re.sub(r"<[^>]+>", "", html)
    text = unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()[:max_chars]


async def _http_get(url: str, timeout: float, headers: Optional[Dict[str, str]] = None):
    """Issue an HTTP GET. Tries httpx, falls back to urllib (so this works
    on a bare Python install too)."""
    try:
        import httpx  # type: ignore
    except ImportError:
        # urllib fallback (sync, run in executor)
        import urllib.request

        def _do():
            req = urllib.request.Request(url, headers=headers or {"User-Agent": _DEFAULT_UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, dict(resp.headers), resp.read()

        return await asyncio.get_event_loop().run_in_executor(None, _do)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        r = await client.get(url, headers=headers or {"User-Agent": _DEFAULT_UA})
        return r.status_code, dict(r.headers), r.content


class HttpGetTool(Tool):
    name = "http_get"
    description = "GET an HTTP(S) URL. Returns status, headers, and body (truncated)."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "timeout": {"type": "number", "default": _DEFAULT_TIMEOUT},
            "max_bytes": {"type": "integer", "default": 200_000},
        },
        "required": ["url"],
    }

    async def run(self, url: str, timeout: float = _DEFAULT_TIMEOUT,
                  max_bytes: int = 200_000) -> ToolResult:
        if not _is_safe_url(url):
            return ToolResult(ok=False, error="URL must be http(s) and not a private/loopback host")
        try:
            status, headers, body = await _http_get(url, timeout)
        except Exception as e:
            return ToolResult(ok=False, error=f"{type(e).__name__}: {e}")
        truncated = body[: int(max_bytes)]
        return ToolResult(
            ok=200 <= status < 300,
            output=truncated.decode("utf-8", errors="replace"),
            error=None if 200 <= status < 300 else f"HTTP {status}",
            meta={"status": status, "headers": headers, "bytes": len(body),
                  "truncated": len(body) > max_bytes},
        )


class WebFetchTool(Tool):
    name = "web_fetch"
    description = "Fetch a webpage and return readable text (HTML stripped)."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "timeout": {"type": "number", "default": _DEFAULT_TIMEOUT},
            "max_chars": {"type": "integer", "default": 20_000},
        },
        "required": ["url"],
    }

    async def run(self, url: str, timeout: float = _DEFAULT_TIMEOUT,
                  max_chars: int = 20_000) -> ToolResult:
        if not _is_safe_url(url):
            return ToolResult(ok=False, error="URL must be http(s) and not a private/loopback host")
        try:
            status, headers, body = await _http_get(url, timeout)
        except Exception as e:
            return ToolResult(ok=False, error=f"{type(e).__name__}: {e}")
        if not (200 <= status < 300):
            return ToolResult(ok=False, error=f"HTTP {status}", meta={"status": status})
        text = _strip_html(body.decode("utf-8", errors="replace"), max_chars=int(max_chars))
        return ToolResult(ok=True, output=text, meta={"status": status, "url": url})


def _is_safe_url(url: str) -> bool:
    try:
        u = urlparse(url)
    except Exception:
        return False
    if u.scheme not in ("http", "https"):
        return False
    host = (u.hostname or "").lower()
    if not host:
        return False
    # Block obvious internal targets — real SSRF protection would resolve DNS.
    bad = ("localhost", "127.", "0.0.0.0", "169.254.", "10.", "192.168.")
    if any(host == b or host.startswith(b) for b in bad):
        return False
    return True
