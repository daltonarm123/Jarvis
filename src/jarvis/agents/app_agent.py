"""App Jarvis — scaffold mobile applications for iOS and Android.

Produces a JSON scaffold of files for simple starter apps (Flutter, React Native,
or native templates). When `ALLOW_APP_AUTO_APPLY=true` the agent may write the
scaffold into `apps/<app_name>/` under the repository root.
"""

from __future__ import annotations

from typing import List
import os
import re
import json
from pathlib import Path

from jarvis.agents.base_agent import BaseAgent, Capability, TaskContext
from jarvis.llm import LLMMessage, get_provider


class AppAgent(BaseAgent):
    name = "app"
    description = "Scaffold mobile apps for iOS and Android (Flutter, React Native, native)."
    provider = "openai"
    model = "gpt-4o-mini"
    system_prompt = (
        "You are App Jarvis. Your job is to create small, well-structured starter app "
        "scaffolds for iOS and Android. When asked to 'create app <name> --framework=<f>' "
        "produce a JSON object with keys: 'app_name', 'framework', 'files' where 'files' is "
        "a list of {\"path\": str, \"content\": str, \"rationale\": str}.\n"
        "Keep templates minimal but runnable where possible. Do NOT execute any code."
    )

    @classmethod
    def capabilities(cls) -> List[Capability]:
        return [
            Capability("mobile_scaffold", "Scaffold simple mobile apps for iOS and Android.", ["app", "mobile", "ios", "android", "flutter", "react native", "scaffold"]),
        ]

    def __init__(self) -> None:
        # Fallback provider selection: prefer OpenAI, fall back to Anthropic if configured
        try:
            if not get_provider("openai").is_configured() and get_provider("anthropic").is_configured():
                self.provider = "anthropic"
                self.model = "claude-3-5-sonnet-latest"
        except KeyError:
            pass

    async def handle(self, ctx: TaskContext) -> str:
        text = (ctx.user_input or "").strip()

        # Simple create command: create app <name> [--framework=flutter|react-native|native]
        m = re.match(r"^(?:create|scaffold|init) app (\S+)(?:\s+--framework=(\S+))?", text, re.I)
        if not m:
            return await super().handle(ctx)

        app_name = m.group(1)
        framework = (m.group(2) or "flutter").lower()

        repo_root = Path(__file__).resolve().parents[3]

        user_msg = (
            f"Create a starter {framework} app named {app_name}. Return a JSON object only:\n"
            "{\"app_name\":str, \"framework\":str, \"files\":[{\"path\":str, \"content\":str, \"rationale\":str}]}\n"
            "Provide minimal runnable code where feasible and small README explaining how to build/run."
        )

        provider = get_provider(self.provider)
        resp = await provider.complete([
            LLMMessage(role="system", content=self.system_prompt),
            LLMMessage(role="user", content=user_msg),
        ], model=self.model, system=self.system_prompt, max_tokens=1500)

        text_out = resp.content
        jm = re.search(r"\{.*\}", text_out, re.DOTALL)
        j = None
        if jm:
            try:
                j = json.loads(jm.group(0))
            except json.JSONDecodeError:
                j = None

        if not j or not isinstance(j.get("files"), list):
            return "App scaffold generation failed: LLM did not return expected JSON. Full response:\n" + text_out

        files = j["files"]
        applied = []
        skipped = []
        if os.getenv("ALLOW_APP_AUTO_APPLY", "false").lower() == "true":
            base = repo_root / "apps" / app_name
            try:
                base.mkdir(parents=True, exist_ok=True)
                for f in files:
                    p = f.get("path")
                    c = f.get("content")
                    if not p or c is None:
                        skipped.append(p or "(missing)")
                        continue
                    tgt = (base / p).resolve()
                    try:
                        tgt.relative_to(repo_root)
                    except Exception:
                        skipped.append(p)
                        continue
                    tgt.parent.mkdir(parents=True, exist_ok=True)
                    tgt.write_text(c)
                    applied.append(str(tgt.relative_to(repo_root)))
            except Exception as e:
                return f"Failed to write scaffold files: {e}"

        out = [f"Scaffold for {app_name} ({framework}) generated."]
        if applied:
            out.append("Applied files:\n" + "\n".join(f" - {p}" for p in applied))
        out.append("Suggested files (JSON):\n" + jm.group(0))
        return "\n\n".join(out)
