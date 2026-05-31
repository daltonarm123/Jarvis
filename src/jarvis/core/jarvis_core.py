"""Jarvis orchestrator.

Owns:
  - the agent registry
  - the router
  - the memory store
  - the conversation loop

Front-ends (CLI, Discord, voice) call `JarvisCore.handle(user_input)` —
that's the single integration point.
"""

from __future__ import annotations

import asyncio
import os
import re
import time
import uuid
from typing import List, Optional

from jarvis.agents import ALL_AGENTS, BaseAgent, TaskContext
from jarvis.agents.manager_agent import ManagerAgent
from jarvis.communication.voice_interface import VoiceInterface
from jarvis.core.automation import TaskMonitor
from jarvis.core.router import JarvisRouter
from jarvis.core.health import HealthMonitor
from jarvis.memory import MemoryStore


class JarvisCore:
    def __init__(self, session_id: Optional[str] = None) -> None:
        self.session_id = session_id or f"cli-{uuid.uuid4().hex[:8]}"
        self.memory = MemoryStore(os.getenv("DATA_DIR", "./data") + "/jarvis.db")
        self.agents: List[BaseAgent] = [cls() for cls in ALL_AGENTS]
        self.router = JarvisRouter(self.agents)
        self.manager = ManagerAgent()
        self.health = HealthMonitor()
        self.task_monitor = TaskMonitor(self.memory)
        self.autonomous_mode = os.getenv("JARVIS_MODE", "interactive") == "autonomous"
        self.autonomous_interval = int(os.getenv("JARVIS_AUTONOMOUS_INTERVAL", str(24 * 60 * 60)))

    # ---------- main entry point ----------

    async def handle(self, user_input: str) -> str:
        text = user_input.strip()
        if not text:
            return ""

        wake_payload = self._extract_wake_phrase(text)
        if wake_payload is not None:
            return await self._handle_wake_phrase(wake_payload)

        # Slash-style commands bypass the router.
        if text.startswith("/"):
            return await self._handle_command(text[1:])

        # Direct address: "@dev refactor this" → forces routing.
        forced = self._extract_at_mention(text)
        if forced:
            agent_name, payload = forced
            agent = next((a for a in self.agents if a.name == agent_name), None)
            if agent is None:
                return f"No agent named '{agent_name}'. Try /agents."
            return await self._dispatch(agent, payload)

        agent = await self.router.route(text)
        return await self._dispatch(agent, text)

    # ---------- internals ----------

    async def _dispatch(self, agent: BaseAgent, user_input: str) -> str:
        self.memory.add_message(self.session_id, "user", user_input, agent=agent.name)
        history = self.memory.recent_messages(self.session_id, limit=20)
        ctx = TaskContext(
            session_id=self.session_id,
            user_input=user_input,
            history=history,
            memory=self.memory,
        )
        try:
            reply = await agent.handle(ctx)
            self.health.record_success(agent.name)
        except Exception as e:  # don't crash the loop on agent errors
            issue = self.health.record_error(
                agent.name,
                e,
                context={"user_input": user_input, "session": self.session_id},
            )
            reply = f"[{agent.name}] error: {e}"
            if self.health.error_counts.get(agent.name, 0) > 2:
                reply += "\n[System] Multiple errors detected. Run '/escalate' to notify dev team."
        self.memory.add_message(self.session_id, "assistant", reply, agent=agent.name)
        return f"[{agent.name}] {reply}"

    async def _handle_command(self, cmd: str) -> str:
        parts = cmd.split(maxsplit=1)
        head = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""

        if head in ("help", "h", "?"):
            return self._help_text()
        if head == "agents":
            return self._agents_text()
        if head == "status":
            return self._status_text()
        if head in ("briefing", "daily", "standup"):
            return await self._generate_daily_briefing()
        if head == "plans":
            return self._plans_text()
        if head in ("tasks", "work", "todo"):
            return self._tasks_text()
        if head in ("profit", "revenue"):
            return self._profit_text()
        if head in ("issues", "health"):
            return self._health_text()
        if head == "escalate":
            return await self._escalate_issues_to_dev()
        if head in ("ask", "question"):
            personal = next((a for a in self.agents if a.name == "personal"), None)
            return await self._dispatch(personal, rest or "Answer the user's question.") if personal else "Personal agent not available."
        if head == "remember":
            return self._cmd_remember(rest)
        if head == "facts":
            facts = self.memory.all_facts()
            if not facts:
                return "No facts stored."
            return "\n".join(f"- {k}: {v}" for k, v in facts.items())
        if head == "session":
            return f"Session: {self.session_id}"
        return f"Unknown command: /{head}. Try /help."

    def _cmd_remember(self, rest: str) -> str:
        if "=" not in rest:
            return "Usage: /remember key = value"
        key, value = (s.strip() for s in rest.split("=", 1))
        self.memory.set_fact(key, value)
        return f"Remembered: {key} = {value}"

    def _help_text(self) -> str:
        return (
            "Jarvis commands:\n"
            "  /help                   Show this help\n"
            "  /agents                 List specialist agents\n"
            "  /status                 Provider + agent status\n"
            "  /briefing               Generate the daily manager briefing\n"
            "  /plans                  Show current agent plans\n"
            "  /tasks                  Show current team work plan\n"
            "  /health                 Show system health and issues\n"
            "  /escalate               Escalate issues to dev agent for fixes\n"
            "  /ask <question>         Ask Jarvis any general question\n"
            "  /remember key = value   Store a fact\n"
            "  /facts                  Show all stored facts\n"
            "  /session                Show current session id\n"
            "  @<agent> <task>         Force route to a specific agent\n"
            "  <anything else>         Auto-routed by Jarvis"
        )

    def _agents_text(self) -> str:
        out = ["Specialist agents:"]
        for a in self.agents:
            out.append(f"  • {a.name:10s} ({a.provider}/{a.model})")
            out.append(f"    {a.description}")
        return "\n".join(out)

    def _status_text(self) -> str:
        from jarvis.llm import available_providers
        configured = available_providers(only_configured=True)
        all_p = available_providers()
        return (
            f"Session: {self.session_id}\n"
            f"Mode: {'autonomous' if self.autonomous_mode else 'interactive'}\n"
            f"Providers configured: {configured or 'NONE'}\n"
            f"Providers available:  {all_p}\n"
            f"Agents loaded: {len(self.agents)}\n"
            f"Autonomous interval: {self.autonomous_interval}s"
        )

    @staticmethod
    def _extract_at_mention(text: str):
        if not text.startswith("@"):
            return None
        head, _, payload = text[1:].partition(" ")
        if not head or not payload:
            return None
        return head.lower(), payload.strip()

    # ---------- legacy CLI loop ----------

    async def run(self, ui=None) -> None:
        if ui is None:
            from jarvis.communication.user_interface import UserInterface

            ui = UserInterface()

        if self.autonomous_mode:
            await self._run_autonomous(ui)
            return

        print("Jarvis online. Type /help for commands. Ctrl-C or 'quit' to exit.\n")
        while True:
            try:
                user_input = await ui.get_input()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if user_input.strip().lower() in ("quit", "exit"):
                break
            if not user_input.strip():
                continue
            reply = await self.handle(user_input)
            await ui.send_output(reply)
        print("Shutting down Jarvis.")
        self.memory.close()

    async def _run_autonomous(self, ui=None) -> None:
        print("Jarvis running in autonomous manager mode.")
        try:
            while True:
                briefing = await self._generate_daily_briefing()
                output = f"Daily briefing complete.\n\n{briefing}"
                if ui:
                    await ui.send_output(output)
                else:
                    print(output)
                await asyncio.sleep(self.autonomous_interval)
        except asyncio.CancelledError:
            pass
        finally:
            print("Shutting down autonomous Jarvis.")
            self.memory.close()

    async def _generate_daily_briefing(self) -> str:
        facts = self.memory.all_facts()
        facts_text = "\n".join(f"- {k}: {v}" for k, v in facts.items()) or "No stored facts."
        recent = self.memory.recent_messages(self.session_id, limit=30)
        convo_text = "\n".join(
            f"{m['role']}({m.get('agent','')})> {m['content']}" for m in recent
        ) or "No recent conversation."

        prompt = (
            "You are Manager Jarvis. Prepare a daily standup briefing for Dalton, the CEO.\n"
            "Use the facts, recent conversation, and the specialist team to summarize current progress,\n"
            "identify top opportunities, and assign clear priorities for today. Keep the output\n"
            "professional, concise, and action-oriented. Include a short summary, three business\n"
            "priorities, and what each specialist agent should focus on next.\n\n"
            "Facts:\n"
            f"{facts_text}\n\n"
            "Recent conversation:\n"
            f"{convo_text}\n\n"
            "Specialist agents: "
            f"{', '.join(a.name for a in self.agents)}\n"
        )

        ctx = TaskContext(
            session_id=self.session_id,
            user_input=prompt,
            history=recent,
            memory=self.memory,
        )
        briefing = await self.manager.handle(ctx)
        self.memory.set_fact("last_daily_briefing", briefing)
        self.memory.set_fact("last_daily_briefing_ts", time.time())

        agent_plans = {}
        for agent in self.agents:
            plan = await self._assign_agent_daily_plan(agent, briefing)
            agent_plans[agent.name] = plan
            self.memory.set_agent_state(agent.name, {
                "daily_plan": plan,
                "last_briefing": briefing,
                "updated": time.time(),
            })

        self.task_monitor.sync_tasks(agent_plans)

        return briefing

    async def _assign_agent_daily_plan(self, agent: BaseAgent, briefing: str) -> str:
        plan_prompt = (
            f"The manager briefing is below. You are {agent.name} specialist.\n"
            "Based on the briefing, propose 3-5 concrete tasks you should work on today.\n"
            "Format your response as short, numbered or bullet-pointed tasks.\n\n"
            "Manager briefing:\n"
            f"{briefing}"
        )
        recent = self.memory.recent_messages(self.session_id, limit=15)
        ctx = TaskContext(
            session_id=self.session_id,
            user_input=plan_prompt,
            history=recent,
            memory=self.memory,
        )
        try:
            return await agent.handle(ctx)
        except Exception as e:
            return f"[{agent.name}] error generating plan: {e}"

    def _plans_text(self) -> str:
        out = ["Current agent plans:"]
        for agent in self.agents:
            state = self.memory.get_agent_state(agent.name)
            plan = state.get("daily_plan") if state else None
            if plan:
                out.append(f"\n{agent.name}:\n{plan}")
            else:
                out.append(f"{agent.name}: no plan available yet.")
        return "\n".join(out)

    def _tasks_text(self) -> str:
        return self.task_monitor.get_task_summary()

    def _health_text(self) -> str:
        critical = self.health.get_critical_issues()
        unresolved = self.health.get_unresolved_issues()
        if not unresolved:
            return "✓ All systems nominal. No issues detected."
        lines = [f"System Health: {len(unresolved)} unresolved issue(s)\n"]
        for issue in unresolved:
            severity_emoji = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
            }[issue.severity]
            lines.append(f"{severity_emoji} [{issue.agent_name}] {issue.issue_type}: {issue.description}")
        if critical:
            lines.append(f"\n⚠ {len(critical)} critical issue(s) detected. Run '/escalate' to notify dev.")
        return "\n".join(lines)

    def _profit_text(self) -> str:
        facts = self.memory.all_facts()
        profit_items = []
        total = 0.0
        for key, value in facts.items():
            if any(token in key.lower() for token in ["profit", "revenue", "income", "sales", "earnings"]):
                profit_items.append((key, value))
                numeric = self._parse_numeric(value)
                if numeric is not None:
                    total += numeric
        if not profit_items:
            return (
                "No profit or revenue facts are stored yet. "
                "Use /remember profit = 1234 or add revenue data with the appropriate agent."
            )
        lines = ["Profit summary from stored facts:"]
        for key, value in profit_items:
            lines.append(f"  - {key}: {value}")
        if total:
            lines.append(f"Total recognized numeric profit/revenue: ${total:.2f}")
        return "\n".join(lines)

    def _parse_numeric(self, value: object) -> Optional[float]:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            match = re.search(r"[-+]?[0-9]*\.?[0-9]+", value.replace(",", ""))
            if match:
                try:
                    return float(match.group(0))
                except ValueError:
                    return None
        return None

    def _extract_wake_phrase(self, text: str) -> Optional[str]:
        match = re.match(r"^(?:hello|hey)\s+jarvis\b[\s,]*(.*)$", text.strip(), re.IGNORECASE)
        if not match:
            return None
        return match.group(1).strip()

    async def _handle_wake_phrase(self, payload: str) -> str:
        if not payload or any(keyword in payload.lower() for keyword in ["what's going on", "whats going on", "what is going on", "today", "plans"]):
            briefing = self.memory.get_fact("last_daily_briefing")
            if not briefing:
                briefing = await self._generate_daily_briefing()
            tasks = self.task_monitor.get_task_summary()
            profit = self._profit_text()
            return (
                "Hello Dalton. Here is what's going on today:\n\n"
                "Daily briefing:\n"
                f"{briefing}\n\n"
                f"{tasks}\n\n"
                f"{profit}"
            )
        if "profit" in payload.lower() or "revenue" in payload.lower() or "income" in payload.lower():
            return self._profit_text()
        return await self.handle(payload)

    async def _escalate_issues_to_dev(self) -> str:
        critical = self.health.get_critical_issues()
        if not critical:
            return "No critical issues to escalate."
        issues_summary = self.health.format_issues_for_dev()
        dev_agent = next((a for a in self.agents if a.name == "dev"), None)
        if not dev_agent:
            return "Dev agent not available."
        escalation_prompt = (
            "I detected critical issues in the system that need your attention:\n\n"
            f"{issues_summary}\n"
            "Please analyze each issue and suggest fixes or patches. Focus on:\n"
            "1. Root cause analysis\n"
            "2. Recommended code fixes or patches\n"
            "3. Testing strategy to prevent regression"
        )
        recent = self.memory.recent_messages(self.session_id, limit=10)
        ctx = TaskContext(
            session_id=self.session_id,
            user_input=escalation_prompt,
            history=recent,
            memory=self.memory,
        )
        try:
            reply = await dev_agent.handle(ctx)
            self.memory.add_message(
                self.session_id,
                "assistant",
                reply,
                agent="dev",
            )
            return f"[dev] {reply}"
        except Exception as e:
            return f"Error escalating to dev: {e}"
