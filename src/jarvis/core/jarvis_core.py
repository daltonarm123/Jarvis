"""Jarvis orchestrator.

Owns:
  - the agent registry
  - the router
  - the memory store
  - the tool registry
  - the scheduler (background autonomous jobs)
  - the conversation loop

Front-ends (CLI, Discord, voice) call `JarvisCore.handle(user_input)` —
that's the single integration point.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from jarvis.agents import ALL_AGENTS, BaseAgent, TaskContext
from jarvis.core.router import JarvisRouter
from jarvis.memory import MemoryStore
from jarvis.scheduler import Scheduler, AtSchedule, IntervalSchedule, CronSchedule
from jarvis.tools import builtin_tools


class JarvisCore:
    def __init__(self, session_id: Optional[str] = None) -> None:
        self.session_id = session_id or f"cli-{uuid.uuid4().hex[:8]}"
        data_dir = os.getenv("DATA_DIR", "./data")
        self.memory = MemoryStore(data_dir + "/jarvis.db")
        self.tools = builtin_tools(os.getenv("AGENT_WORKSPACE", data_dir + "/agent_workspace"))
        self.agents: List[BaseAgent] = [cls() for cls in ALL_AGENTS]
        self.router = JarvisRouter(self.agents)
        self.autonomous_mode = os.getenv("JARVIS_MODE", "interactive") == "autonomous"
        self.scheduler = Scheduler(
            db_path=data_dir + "/scheduler.db",
            handler=self._scheduler_handler,
        )
        self._briefing_buffer: List[str] = []  # collects briefings for next CLI turn

    # ---------- main entry point ----------

    async def handle(self, user_input: str) -> str:
        text = user_input.strip()
        if not text:
            return ""

        if text.startswith("/"):
            return await self._handle_command(text[1:])

        forced = self._extract_at_mention(text)
        if forced:
            agent_name, payload = forced
            agent = next((a for a in self.agents if a.name == agent_name), None)
            if agent is None:
                return f"No agent named '{agent_name}'. Try /agents."
            return await self._dispatch(agent, payload)

        agent = await self.router.route(text)
        return await self._dispatch(agent, text)

    # ---------- scheduler integration ----------

    async def _scheduler_handler(self, kind: str, payload: Dict[str, Any]) -> str:
        """The scheduler invokes this for every job run."""
        if kind == "agent_task":
            text = payload.get("input", "").strip()
            if not text:
                return "skipped: empty input"
            # Optional explicit agent
            agent_name = payload.get("agent")
            if agent_name:
                agent = next((a for a in self.agents if a.name == agent_name), None)
                if agent is None:
                    raise RuntimeError(f"No agent named '{agent_name}'")
            else:
                agent = await self.router.route(text)
            return await self._dispatch(agent, text, surface="scheduler")

        if kind == "tool_call":
            name = payload["tool"]
            args = payload.get("args", {})
            result = await self.tools.call(name, **args)
            if not result.ok:
                raise RuntimeError(result.error or "tool failed")
            return result.to_text()[:4000]

        if kind == "system_event":
            event = payload.get("event")
            if event == "daily_briefing":
                return await self._daily_briefing()
            return f"unknown system_event: {event}"

        raise RuntimeError(f"Unknown job kind: {kind}")

    async def _daily_briefing(self) -> str:
        """Build today's briefing. Placeholder until analyst agent lands."""
        now = datetime.now(timezone.utc)
        jobs = self.scheduler.list_jobs()
        n_enabled = sum(1 for j in jobs if j.enabled)
        n_failing = sum(1 for j in jobs if (j.failure_count or 0) > 0)
        text = (
            f"🌅 Daily briefing — {now.strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"Scheduled jobs: {len(jobs)} ({n_enabled} enabled, {n_failing} flaky)\n"
            f"Mode: {'autonomous' if self.autonomous_mode else 'interactive'}"
        )
        # Park in buffer so the next CLI turn surfaces it.
        self._briefing_buffer.append(text)
        return text

    # ---------- dispatch ----------

    async def _dispatch(self, agent: BaseAgent, user_input: str, surface: str = "user") -> str:
        self.memory.add_message(self.session_id, "user", user_input, agent=agent.name)
        history = self.memory.recent_messages(self.session_id, limit=20)
        ctx = TaskContext(
            session_id=self.session_id,
            user_input=user_input,
            history=history,
            memory=self.memory,
            tools=self.tools,
        )
        try:
            reply = await agent.handle(ctx)
        except Exception as e:
            reply = f"[{agent.name}] error: {e}"
        self.memory.add_message(self.session_id, "assistant", reply, agent=agent.name)
        return f"[{agent.name}] {reply}"

    # ---------- commands ----------

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
        if head == "remember":
            return self._cmd_remember(rest)
        if head == "facts":
            facts = self.memory.all_facts()
            if not facts:
                return "No facts stored."
            return "\n".join(f"- {k}: {v}" for k, v in facts.items())
        if head == "session":
            return f"Session: {self.session_id}"
        if head == "tools":
            return self._tools_text()
        if head == "tool":
            return await self._cmd_tool(rest)
        if head == "jobs":
            return self._jobs_text()
        if head == "schedule":
            return self._cmd_schedule(rest)
        if head == "unschedule":
            return self._cmd_unschedule(rest)
        if head == "runjob":
            return await self._cmd_runjob(rest)
        if head == "runs":
            return self._cmd_runs(rest)
        return f"Unknown command: /{head}. Try /help."

    # individual command impls ---------------------------------------------

    def _cmd_remember(self, rest: str) -> str:
        if "=" not in rest:
            return "Usage: /remember key = value"
        key, value = (s.strip() for s in rest.split("=", 1))
        self.memory.set_fact(key, value)
        return f"Remembered: {key} = {value}"

    def _tools_text(self) -> str:
        out = ["Available tools:"]
        for t in self.tools.all():
            out.append(f"  \u2022 {t.name:12s} {t.description}")
        return "\n".join(out)

    async def _cmd_tool(self, rest: str) -> str:
        if not rest:
            return "Usage: /tool <name> <json-args>"
        parts = rest.split(maxsplit=1)
        name = parts[0]
        args_text = parts[1] if len(parts) > 1 else "{}"
        try:
            args = json.loads(args_text)
            if not isinstance(args, dict):
                return "args must be a JSON object"
        except json.JSONDecodeError as e:
            return f"Invalid JSON: {e}"
        result = await self.tools.call(name, **args)
        return result.to_text()

    def _jobs_text(self) -> str:
        jobs = self.scheduler.list_jobs()
        if not jobs:
            return "No jobs scheduled. Use /schedule to add one."
        lines = ["Scheduled jobs:"]
        for j in jobs:
            nxt = j.next_run.isoformat(timespec="seconds") if j.next_run else "—"
            tag = "" if j.enabled else " [disabled]"
            err = f" failures={j.failure_count}" if j.failure_count else ""
            lines.append(f"  {j.id:20s} {j.kind:13s} next={nxt}{tag}{err}  ({j.name})")
        return "\n".join(lines)

    def _cmd_schedule(self, rest: str) -> str:
        """
        /schedule <id> <when> <kind> <payload-json>

        when (quote if it has spaces):
          "cron:0 9 * * *"            standard 5-field cron
          "@daily 09:00"              shorthand
          every:30m                   interval (s/m/h/d)
          at:2026-06-01T08:00:00      one-shot ISO datetime

        kind: agent_task | tool_call | system_event
        payload: JSON, e.g. {"input":"morning briefing"}
        """
        import shlex
        try:
            # Split JSON payload off the right first (so its inner quotes survive).
            brace = rest.find("{")
            if brace < 0:
                return "Usage: /schedule <id> <when> <kind> <payload-json>\n" + (self._cmd_schedule.__doc__ or "")
            head, payload_text = rest[:brace].strip(), rest[brace:].strip()
            tokens = shlex.split(head)
            if len(tokens) < 3:
                return "Usage: /schedule <id> <when> <kind> <payload-json>\n" + (self._cmd_schedule.__doc__ or "")
            job_id = tokens[0]
            kind = tokens[-1]
            when = " ".join(tokens[1:-1])
            schedule = _parse_when(when)
            payload = json.loads(payload_text)
            self.scheduler.add_job(
                job_id=job_id, name=job_id, kind=kind, payload=payload,
                schedule=schedule, catch_up=False,
            )
            job = self.scheduler.get_job(job_id)
            return f"Scheduled '{job_id}' ({kind}). Next run: {job.next_run}"
        except Exception as e:
            return f"Schedule error: {e}"

    def _cmd_unschedule(self, rest: str) -> str:
        if not rest:
            return "Usage: /unschedule <id>"
        ok = self.scheduler.remove_job(rest.strip())
        return "Removed." if ok else "Not found."

    async def _cmd_runjob(self, rest: str) -> str:
        if not rest:
            return "Usage: /runjob <id>"
        try:
            run = await self.scheduler.run_now(rest.strip())
            return f"[{run.status}] {run.output or run.error or '(no output)'}"
        except KeyError:
            return f"No job: {rest.strip()}"

    def _cmd_runs(self, rest: str) -> str:
        if not rest:
            return "Usage: /runs <id>"
        runs = self.scheduler.recent_runs(rest.strip(), limit=10)
        if not runs:
            return "No runs yet."
        lines = [f"Recent runs for {rest.strip()}:"]
        for r in runs:
            tag = (r.output or r.error or "")[:80].replace("\n", " ")
            lines.append(f"  {r.started.isoformat(timespec='seconds')}  {r.status:6s}  {tag}")
        return "\n".join(lines)

    def _help_text(self) -> str:
        return (
            "Jarvis commands:\n"
            "  /help                              Show this help\n"
            "  /agents                            List specialist agents\n"
            "  /tools                             List available tools\n"
            "  /tool <name> <json>                Run a tool directly (debug)\n"
            "  /jobs                              List scheduled jobs\n"
            "  /schedule <id> <when> <kind> <pl>  Add a scheduled job\n"
            "  /unschedule <id>                   Remove a scheduled job\n"
            "  /runjob <id>                       Run a job now (off-schedule)\n"
            "  /runs <id>                         Recent run history for a job\n"
            "  /status                            Provider + agent + job status\n"
            "  /remember key = value              Store a fact\n"
            "  /facts                             Show all stored facts\n"
            "  /session                           Show current session id\n"
            "  @<agent> <task>                    Force route to a specific agent\n"
            "  <anything else>                    Auto-routed by Jarvis"
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
        jobs = self.scheduler.list_jobs()
        return (
            f"Session: {self.session_id}\n"
            f"Mode: {'autonomous' if self.autonomous_mode else 'interactive'}\n"
            f"Providers configured: {configured or 'NONE'}\n"
            f"Providers available:  {all_p}\n"
            f"Agents loaded: {len(self.agents)}\n"
            f"Jobs scheduled: {len(jobs)} ({sum(1 for j in jobs if j.enabled)} enabled)"
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

    async def run(self) -> None:
        from jarvis.communication.user_interface import UserInterface
        ui = UserInterface()
        await self.scheduler.start()
        print("Jarvis online. Type /help for commands. Ctrl-C or 'quit' to exit.\n")
        try:
            while True:
                # Drain any briefing(s) that fired in the background.
                while self._briefing_buffer:
                    await ui.send_output(self._briefing_buffer.pop(0))
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
        finally:
            print("Shutting down Jarvis.")
            await self.scheduler.stop()
            self.memory.close()


# ---------- helpers ----------

def _parse_when(when: str):
    """Parse a /schedule when-spec into a Schedule."""
    when = when.strip()
    if when.startswith("cron:"):
        return CronSchedule(when[len("cron:"):].strip().strip('"'))
    if when.startswith("@daily"):
        return CronSchedule(when)
    if when.startswith("every:"):
        spec = when[len("every:"):].strip()
        # e.g. 30s, 5m, 2h, 1d
        unit = spec[-1].lower()
        n = int(spec[:-1])
        seconds = {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit] * n
        return IntervalSchedule(seconds=seconds)
    if when.startswith("at:"):
        return AtSchedule(when=datetime.fromisoformat(when[len("at:"):]))
    raise ValueError(f"Unrecognized when spec: {when!r}")
