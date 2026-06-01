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
from typing import Dict, List, Optional

from jarvis.agents import ALL_AGENTS, BaseAgent, TaskContext
from jarvis.agents.manager_agent import ManagerAgent
from jarvis.communication.voice_interface import VoiceInterface
from jarvis.core.automation import ScheduleManager, TaskMonitor
from jarvis.core.router import JarvisRouter
from jarvis.core.health import HealthMonitor
from jarvis.memory import MemoryStore
from jarvis.platforms.registry import get_connector


class JarvisCore:
    def __init__(self, session_id: Optional[str] = None) -> None:
        self.session_id = session_id or f"cli-{uuid.uuid4().hex[:8]}"
        self.memory = MemoryStore(os.getenv("DATA_DIR", "./data") + "/jarvis.db")
        self.agents: List[BaseAgent] = [cls() for cls in ALL_AGENTS]
        self.router = JarvisRouter(self.agents)
        self.manager = ManagerAgent()
        self.health = HealthMonitor()
        self.task_monitor = TaskMonitor(self.memory)
        self.schedule_manager = ScheduleManager(self.memory)
        self.autonomous_mode = os.getenv("JARVIS_MODE", "interactive") == "autonomous"
        self.autonomous_interval = int(os.getenv("JARVIS_AUTONOMOUS_INTERVAL", str(24 * 60 * 60)))
        self.publish_interval = int(os.getenv("JARVIS_PUBLISH_INTERVAL", str(5 * 60)))

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
        if head in ("accounts", "account"):
            return await self._account_text(head, rest)
        if head == "schedule":
            return await self._schedule_text(rest)
        if head == "publish":
            return await self._publish_text(rest)
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
            "  /accounts               List social accounts and credential status\n"
            "  /account <platform>     Show details for a social account\n"
            "  /account add platform=<platform> alias=<alias>  Register a new social account\n"
            "  /account credentials platform=<platform> alias=<alias> <fields>  Store account credentials\n"
            "  /schedule               Manage scheduled publishing jobs\n"
            "  /publish <now|status>   Trigger or inspect publishing\n"
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
            f"Autonomous interval: {self.autonomous_interval}s\n"
            f"Publish interval: {self.publish_interval}s"
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
            publish_task = asyncio.create_task(self._run_autonomous_publish(ui))
            briefing_task = asyncio.create_task(self._run_autonomous(ui))
            try:
                await asyncio.gather(briefing_task, publish_task)
            finally:
                publish_task.cancel()
                briefing_task.cancel()
                await asyncio.gather(publish_task, briefing_task, return_exceptions=True)
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

    async def _run_autonomous_publish(self, ui=None) -> None:
        print(f"Jarvis scheduled publishing loop starting every {self.publish_interval} seconds.")
        try:
            while True:
                result = await self._run_scheduled_posts(quiet=True)
                if result:
                    message = f"Scheduled publish check:\n{result}"
                    if ui:
                        await ui.send_output(message)
                    else:
                        print(message)
                await asyncio.sleep(self.publish_interval)
        except asyncio.CancelledError:
            pass
        finally:
            print("Shutting down scheduled publishing loop.")

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

    async def _account_text(self, head: str, rest: str) -> str:
        if head == "accounts":
            return self._list_accounts_text()
        if not rest:
            return self._list_accounts_text()

        raw = rest.strip()
        if raw.lower() in ("list", "show", "all"):
            return self._list_accounts_text()

        command_word = raw.split(maxsplit=1)[0].lower()
        if command_word in ("add", "create", "remove", "delete", "credentials", "cred", "update"):
            return await self._account_command_text(raw)

        params = self._parse_key_value_args(raw)
        platform = params.get("platform") or self._normalize_platform(raw)
        if platform:
            return self._account_detail_text(platform)

        return self._list_accounts_text()

    async def _account_command_text(self, raw: str) -> str:
        parts = raw.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        params = self._parse_key_value_args(args)

        if command in ("add", "create"):
            if "platform" in params:
                phrase = f"create account for {params['platform']}"
                if params.get("alias"):
                    phrase += f" as {params['alias']}"
                return await self._delegate_to_social_agent(phrase)
            return await self._delegate_to_social_agent(raw)

        if command in ("remove", "delete"):
            if "platform" in params and "alias" in params:
                return await self._delegate_to_social_agent(
                    f"remove account for {params['platform']} {params['alias']}"
                )
            return await self._delegate_to_social_agent(raw)

        if command in ("credentials", "cred", "update"):
            if "platform" in params and "alias" in params:
                credential_text = " ".join(
                    f"{k}={v}"
                    for k, v in params.items()
                    if k not in ("platform", "alias")
                )
                phrase = f"add credentials for {params['platform']} {params['alias']} {credential_text}".strip()
                return await self._delegate_to_social_agent(phrase)
            return await self._delegate_to_social_agent(raw)

        return self._list_accounts_text()

    async def _delegate_to_social_agent(self, payload: str) -> str:
        social = next((a for a in self.agents if a.name == "social"), None)
        if not social:
            return "Social agent not available."
        return await self._dispatch(social, payload)

    def _list_accounts_text(self) -> str:
        state = self.memory.get_agent_state("social")
        accounts = state.get("accounts", []) if state else []
        if not accounts:
            return "No social accounts are registered yet. Use '/account <platform>' or 'create account for <platform>'."
        lines = ["Social accounts:"]
        for account in accounts:
            alias = account.get("alias", "unnamed")
            platform = account.get("platform", "unknown")
            status = account.get("status", "unknown")
            cred_flag = "✓" if account.get("has_credentials") else "⚠"
            lines.append(f"  • {alias} ({platform}) - {status} [{cred_flag} credentials]")
        return "\n".join(lines)

    def _account_detail_text(self, rest: str) -> str:
        platform = self._normalize_platform(rest.lower())
        if not platform:
            return "Please specify which platform account to show: TikTok, Instagram, Facebook, or YouTube."
        state = self.memory.get_agent_state("social")
        accounts = state.get("accounts", []) if state else []
        matches = [a for a in accounts if a.get("platform") == platform]
        if not matches:
            return f"No registered account found for {platform}. Use '/account' to list accounts."
        lines = [f"Accounts for {platform}:"]
        for account in matches:
            alias = account.get("alias", "unnamed")
            status = account.get("status", "unknown")
            notes = account.get("notes", "none")
            creds = "yes" if account.get("has_credentials") else "no"
            lines.append(f"  • {alias}: status={status}, credentials={creds}, notes={notes}")
        return "\n".join(lines)

    async def _schedule_text(self, rest: str) -> str:
        if not rest or rest.strip() in ("list", "show", "all"):
            return self.schedule_manager.get_schedule_summary()

        parts = rest.strip().split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command in ("add", "create"):
            params = self._parse_key_value_args(args)
            missing = [k for k in ("platform", "video_path", "title", "caption", "when") if k not in params]
            if missing:
                return (
                    "Missing schedule fields: " + ", ".join(missing) + ". "
                    "Use '/schedule add platform=<platform> alias=<alias> video_path=<path> title='<title>' caption='<caption>' when=<when> tags=<tag1,tag2>'."
                )
            platform = params["platform"]
            alias = params.get("alias")
            account_auto_created = False
            if not alias:
                aliases = self._list_social_aliases(platform)
                if len(aliases) == 1:
                    alias = aliases[0]
                elif len(aliases) == 0:
                    alias = self._suggest_social_alias(platform)
                    self._ensure_social_account(platform, alias, status="pending")
                    account_auto_created = True
                else:
                    return (
                        "Multiple accounts exist for this platform. Please specify alias=... in your schedule command."
                    )
            elif not self._social_account_exists(platform, alias):
                self._ensure_social_account(platform, alias, status="pending")
                account_auto_created = True

            tags = [t.strip() for t in params.get("tags", "").replace("#", "").split(",") if t.strip()]
            item = self.schedule_manager.add_schedule(
                platform=platform,
                alias=alias,
                video_path=params["video_path"],
                title=params["title"],
                caption=params["caption"],
                tags=tags,
                when=params["when"],
            )
            response = (
                f"Scheduled post {item.id} for {item.platform}/{item.alias} at "
                f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(item.scheduled_at))}."
            )
            if account_auto_created:
                response += (
                    f" Account '{alias}' was auto-registered with pending status. "
                    f"Add credentials with '/account credentials platform={platform} alias={alias} <fields>'."
                )
            return response

        if command in ("run", "execute", "due"):
            return await self._run_scheduled_posts()

        if command in ("remove", "delete"):
            if not args:
                return "Specify the schedule ID to remove: '/schedule remove <id>'."
            removed = self.schedule_manager.remove_schedule(args.strip())
            return "Schedule removed." if removed else "Schedule ID not found."

        return (
            "Schedule commands:\n"
            "  /schedule list\n"
            "  /schedule add platform=<platform> alias=<alias> video_path=<path> title='<title>' caption='<caption>' when=<when> tags=<tag1,tag2>\n"
            "  /schedule run\n"
            "  /schedule remove <id>\n"
        )

    async def _publish_text(self, rest: str) -> str:
        if not rest or rest.strip() == "status":
            return self.schedule_manager.get_schedule_summary()
        if rest.strip() == "now":
            return await self._run_scheduled_posts()
        return "Use '/publish now' to execute due scheduled posts or '/publish status' to inspect the queue."

    async def _run_scheduled_posts(self, quiet: bool = False) -> str:
        due = self.schedule_manager.get_due_schedules()
        if not due:
            return "" if quiet else "No scheduled posts are due right now."

        results = []
        social = next((a for a in self.agents if a.name == "social"), None)
        if not social:
            return "Social agent not available for publishing."

        for item in due:
            account = self._find_social_account(item.platform, item.alias)
            if not account:
                results.append(
                    f"{item.id}: account {item.alias} not found for {item.platform}. "
                    f"Create it with '/account add platform={item.platform} alias={item.alias}'."
                )
                self.schedule_manager.set_schedule_status(item.id, "failed")
                continue
            if not account.get("has_credentials"):
                results.append(
                    f"{item.id}: credentials missing for account {item.alias}. "
                    f"Add them with '/account credentials platform={item.platform} alias={item.alias} <fields>'."
                )
                self.schedule_manager.set_schedule_status(item.id, "failed")
                continue
            connector = get_connector(item.platform)
            try:
                result = await asyncio.to_thread(
                    connector.post_video,
                    item.platform,
                    account,
                    item.video_path,
                    item.title,
                    item.caption,
                    item.tags,
                )
            except Exception as exc:
                result = {"success": False, "message": f"Connector error: {exc}"}

            if not result.get("success") and os.getenv("JARVIS_SIMULATE_POSTING", "").lower() in ("1", "true", "yes"):
                result = {
                    "success": True,
                    "message": "Simulated post execution because JARVIS_SIMULATE_POSTING is enabled.",
                }
            status = "completed" if result.get("success") else "failed"
            self.schedule_manager.set_schedule_status(item.id, status)
            results.append(f"{item.id}: {result.get('message', 'Done')} [{status}]")
        return "\n".join(results)

    def _get_social_state(self) -> Dict[str, Any]:
        return self.memory.get_agent_state("social") or {}

    def _save_social_state(self, state: Dict[str, Any]) -> None:
        self.memory.set_agent_state("social", state)

    def _list_social_aliases(self, platform: str) -> List[str]:
        state = self._get_social_state()
        return [a.get("alias") for a in state.get("accounts", []) if a.get("platform") == platform]

    def _social_account_exists(self, platform: str, alias: str) -> bool:
        return alias in self._list_social_aliases(platform)

    def _suggest_social_alias(self, platform: str) -> str:
        existing = set(self._list_social_aliases(platform))
        base = f"{platform}_account"
        alias = base
        counter = 1
        while alias in existing:
            counter += 1
            alias = f"{base}{counter}"
        return alias

    def _ensure_social_account(self, platform: str, alias: str, status: str = "pending") -> None:
        state = self._get_social_state()
        accounts = state.get("accounts", [])
        if not any(a.get("platform") == platform and a.get("alias") == alias for a in accounts):
            accounts.append(
                {
                    "platform": platform,
                    "alias": alias,
                    "status": status,
                    "notes": "created by schedule automation",
                    "has_credentials": False,
                }
            )
            state["accounts"] = accounts
            self._save_social_state(state)

    def _find_social_account(self, platform: str, alias: str) -> Optional[Dict[str, Any]]:
        state = self._get_social_state()
        accounts = state.get("accounts", [])
        for account in accounts:
            if account.get("platform") == platform and account.get("alias") == alias:
                social = next((a for a in self.agents if a.name == "social"), None)
                if social:
                    ctx = TaskContext(
                        session_id=self.session_id,
                        user_input="",
                        history=[],
                        memory=self.memory,
                    )
                    try:
                        vault = social._get_vault(ctx)
                        creds = vault.get(platform, alias)
                        if creds:
                            account["credentials"] = creds
                            if not account.get("has_credentials"):
                                account["has_credentials"] = True
                                self._save_social_state(state)
                    except Exception:
                        pass
                return account
        return None

    def _normalize_platform(self, text: str) -> Optional[str]:
        platform = text.strip().lower()
        if platform in ("tiktok", "tt"):
            return "tiktok"
        if platform in ("instagram", "ig", "insta"):
            return "instagram"
        if platform in ("facebook", "fb"):
            return "facebook"
        if platform in ("youtube", "yt"):
            return "youtube"
        return None

    def _parse_key_value_args(self, text: str) -> Dict[str, str]:
        params: Dict[str, str] = {}
        if not text:
            return params
        pattern = r"(\w+)=('(?:[^']*)'|\"(?:[^\"]*)\"|[^\s]+)"
        for match in re.finditer(pattern, text):
            key = match.group(1)
            value = match.group(2)
            if value.startswith("'") and value.endswith("'") or value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            params[key] = value
        return params

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
