"""Dev Jarvis — coding, debugging, refactors, GitHub work."""

from __future__ import annotations

from typing import List

from jarvis.agents.base_agent import BaseAgent, Capability


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
