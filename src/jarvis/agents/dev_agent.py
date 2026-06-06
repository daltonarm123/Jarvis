"""Dev Jarvis — coding, debugging, refactors, GitHub work."""

from __future__ import annotations

from typing import List
import os
import re
import json
from pathlib import Path

from jarvis.agents.base_agent import BaseAgent, Capability, TaskContext
from jarvis.llm import LLMMessage, get_provider


class DevAgent(BaseAgent):
    name = "dev"
    description = "Software engineering: code, debugging, refactors, GitHub, code review."
    provider = "anthropic"
    model = "claude-3-5-sonnet-latest"
    system_prompt = (
        "You are Dev Jarvis, a senior software engineer assisting Dalton.\n"
        "Prioritize correctness, clean architecture, and explanation of risk before destructive changes.\n"
        "Default tone: concise, technical, opinionated. Never invent APIs.\n"
        "When asked to write code, prefer modular structure and include comments on non-obvious logic.\n"
        "When asked to debug, identify root causes first; offer multiple solutions when relevant."
    )

    def __init__(self) -> None:
        # Fallback if Anthropic isn't configured: degrade to OpenAI.
        from jarvis.llm import get_provider

        try:
            if not get_provider("anthropic").is_configured() and get_provider("openai").is_configured():
                self.provider = "openai"
                self.model = "gpt-4o"
        except KeyError:
            pass

    async def handle(self, ctx: TaskContext) -> str:
        """Enhanced handler: supports file review and simple auto-apply patches.

        Commands recognized (natural language):
        - "review file <path>"  -> returns review + suggested patch(es)
        - "fix file <path>"     -> returns review and (optionally) applies simple fixes

        If environment `ALLOW_DEV_AUTO_APPLY` is set to "true", patches marked
        `simple: true` in the LLM output will be written to disk automatically.
        """
        text = (ctx.user_input or "").strip()

        # Detect simple file review/fix patterns
        m = re.match(r"^(?:review|audit) file (.+)$", text, re.I)
        fm = re.match(r"^(?:fix|repair|apply) file (.+)$", text, re.I)
        if not (m or fm):
            # fallback to default behavior
            return await super().handle(ctx)

        file_path = (m or fm).group(1).strip()
        # Resolve relative to repo root for safety
        repo_root = Path(__file__).resolve().parents[3]
        target = (repo_root / file_path).resolve()
        try:
            target.relative_to(repo_root)
        except Exception:
            return f"[{self.name}] Error: path {file_path} is outside the repository root."

        if not target.exists():
            return f"[{self.name}] Error: file not found: {file_path}"

        content = target.read_text()

        system = (
            self.system_prompt
            + "\nWhen suggesting changes, return a JSON object inside a single JSON code block."
            + "\nThe JSON must contain: {\"summary\":str, \"patches\": [{\"path\":str, \"content\":str, \"simple\":bool, \"rationale\":str}]}"
        )

        user_msg = (
            f"Review the file at: {file_path}\n---FILE-CONTENT-START---\n{content}\n---FILE-CONTENT-END---\n\n"
            "Provide: 1) a concise summary of issues found, 2) suggested replacement content for the file (if any).\n"
            "Output the machine-readable suggestion as a JSON object inside a single JSON code block.\n"
            "Only include the JSON in the code block; also include a short human-readable summary before it."
        )

        provider = get_provider(self.provider)
        resp = await provider.complete(
            [LLMMessage(role="system", content=system), LLMMessage(role="user", content=user_msg)],
            model=self.model,
            system=self.system_prompt,
            max_tokens=1500,
        )

        text_out = resp.content

        # Try to extract JSON from response
        j = None
        jm = re.search(r"\{.*\}", text_out, re.DOTALL)
        if jm:
            try:
                j = json.loads(jm.group(0))
            except json.JSONDecodeError:
                j = None

        applied = []
        skipped = []
        if j and isinstance(j.get("patches"), list):
            allow_auto = os.getenv("ALLOW_DEV_AUTO_APPLY", "false").lower() == "true"
            for p in j.get("patches", []):
                ppath = p.get("path")
                pcontent = p.get("content")
                simple = bool(p.get("simple"))
                if not ppath or pcontent is None:
                    skipped.append(ppath or "(missing path)")
                    continue
                tgt = (repo_root / ppath).resolve()
                try:
                    tgt.relative_to(repo_root)
                except Exception:
                    skipped.append(ppath)
                    continue

                if allow_auto and simple:
                    tgt.write_text(pcontent)
                    applied.append(ppath)
                else:
                    skipped.append(ppath)

        # Build the returned message
        out_lines = []
        if fm:
            out_lines.append("Applied auto-fixes for simple patches." if applied else "No auto-applied patches.")
        else:
            out_lines.append("Review complete. Suggested changes follow.")

        if applied:
            out_lines.append("Applied:\n" + "\n".join(f" - {p}" for p in applied))
        if skipped:
            out_lines.append("Suggested (not applied):\n" + "\n".join(f" - {p}" for p in skipped))

        # Append the LLM's human-readable content (without the JSON) if present
        if jm:
            human = text_out[: jm.start()].strip()
            if human:
                out_lines.append("Details:\n" + human)
            # include the JSON block for transparency
            out_lines.append("Suggested JSON:\n" + jm.group(0))
        else:
            out_lines.append("LLM response did not contain a JSON suggestions block. Full response:\n" + text_out)

        return "\n\n".join(out_lines)

    @classmethod
    def capabilities(cls) -> List[Capability]:
        return [
            Capability(
                "write_code",
                "Write, refactor, or modify source code in any language.",
                ["code", "function", "refactor", "implement", "bug", "debug",
                 "python", "javascript", "lua", "typescript", "rust", "go",
                 "class", "module", "library", "script"],
            ),
            Capability(
                "code_review",
                "Review existing code and suggest improvements.",
                ["review", "look at", "check", "audit"],
            ),
            Capability(
                "github_ops",
                "Work with GitHub repos: clone, branch, commit, push, PR.",
                ["github", "repo", "repository", "pull request", "pr",
                 "commit", "push", "branch", "merge"],
            ),
        ]
