"""Core Jarvis class that manages agents and user interactions."""

import asyncio
import os
from typing import List
from jarvis.agents.base_agent import BaseAgent
from jarvis.communication.user_interface import UserInterface
from jarvis.config import AGENT_CONFIG
from jarvis.utils.daily_reporter import DailyReporter
from jarvis.utils.finance_tracker import FinanceTracker


class JarvisCore:
    """Central controller for the Jarvis system."""

    def __init__(self):
        self.agents: List[BaseAgent] = []
        self.user_interface = UserInterface()
        self.reporter = DailyReporter()
        self.finance_tracker = FinanceTracker()
        self.autonomous_mode = os.getenv("JARVIS_MODE", "interactive") == "autonomous"
        self._initialize_agents()

    def _initialize_agents(self):
        """Initialize the default set of agents."""
        # For now, create placeholder agents
        # In the future, load from config or dynamically
        from jarvis.agents.content_creator import ContentCreatorAgent
        from jarvis.agents.video_editor import VideoEditorAgent
        from jarvis.agents.stream_clipper import StreamClipperAgent
        from jarvis.agents.social_poster import SocialPosterAgent
        from jarvis.agents.ecommerce_agent import EcommerceAgent
        from jarvis.agents.marketing_agent import MarketingAgent

    def _initialize_agents(self):
        """Initialize the default set of agents."""
        # For now, create placeholder agents
        # In the future, load from config or dynamically
        from jarvis.agents.content_creator import ContentCreatorAgent
        from jarvis.agents.video_editor import VideoEditorAgent
        from jarvis.agents.stream_clipper import StreamClipperAgent
        from jarvis.agents.social_poster import SocialPosterAgent
        from jarvis.agents.ecommerce_agent import EcommerceAgent
        from jarvis.agents.marketing_agent import MarketingAgent

        self.agents = [
            ContentCreatorAgent("Content Creator 1", self, AGENT_CONFIG["Content Creator 1"]["ai_model"]),
            VideoEditorAgent("Video Editor 1", self, AGENT_CONFIG["Video Editor 1"]["ai_model"]),
            StreamClipperAgent("Stream Clipper 1", self, AGENT_CONFIG["Stream Clipper 1"]["ai_model"]),
            SocialPosterAgent("Social Poster 1", self, AGENT_CONFIG["Social Poster 1"]["ai_model"]),
            EcommerceAgent("E-commerce Agent 1", self, AGENT_CONFIG["E-commerce Agent 1"]["ai_model"]),
            MarketingAgent("Marketing Agent 1", self, AGENT_CONFIG["Marketing Agent 1"]["ai_model"]),
            # Add more agents as needed
        ]

    async def run(self):
        """Main run loop for Jarvis."""
        print("Jarvis is running. Type 'help' for commands.")

        while True:
            user_input = await self.user_interface.get_input()
            if user_input.lower() in ['quit', 'exit']:
                break
            elif user_input.lower() == 'help':
                self._show_help()
            elif user_input.lower().startswith('agent '):
                await self._handle_agent_command(user_input)
            else:
                response = await self._process_command(user_input)
                await self.user_interface.send_output(response)

        print("Shutting down Jarvis...")

    def _show_help(self):
        """Display help information."""
        help_text = """
Available commands:
- help: Show this help
- briefing: Get daily report and plan
- agent <name> <command>: Send command to specific agent
- status: Show system status
- quit/exit: Shutdown Jarvis
        """
        print(help_text)

    async def _handle_agent_command(self, command: str):
        """Handle commands directed to agents."""
        parts = command.split(' ', 2)
        if len(parts) < 3:
            print("Usage: agent <name> <command>")
            return

        agent_name = parts[1]
        agent_command = parts[2]

        agent = next((a for a in self.agents if a.name == agent_name), None)
        if agent:
            result = await agent.execute_command(agent_command)
            print(f"Agent {agent_name}: {result}")
        else:
            print(f"Agent {agent_name} not found.")

    async def _process_command(self, command: str) -> str:
        """Process general commands."""
        if command.lower() == 'status':
            return self._get_status()
        elif command.lower() == 'briefing':
            return await self.get_daily_briefing()
        else:
            return f"Unknown command: {command}"

    async def report_issue(self, agent_name: str, issue: str):
        """Receive issue reports from agents."""
        print(f"[JARVIS] Received issue from {agent_name}: {issue}")
        # In the future, analyze the issue and provide solutions
        solution = await self._analyze_issue(issue)
        print(f"[JARVIS] Suggested solution: {solution}")
        return solution

    async def _analyze_issue(self, issue: str) -> str:
        """Analyze an issue and suggest a solution."""
        # Simple rule-based analysis for now
        if "conversion" in issue.lower():
            return "Try A/B testing different landing pages or offers."
        elif "ad spend" in issue.lower():
            return "Optimize targeting and ad creative for better ROI."
        elif "low engagement" in issue.lower():
            return "Improve content quality and posting schedule."
        else:
            return "Investigate further and gather more data."

    async def get_daily_briefing(self) -> str:
        """Get daily briefing with yesterday's report and today's plan."""
        yesterday_report = self.reporter.get_yesterday_report()
        today_plan = self.reporter.get_today_plan()

        briefing = "🌅 Good morning! Here's your daily briefing:\n\n"

        briefing += "📊 Yesterday's Summary:\n"
        briefing += f"{yesterday_report['summary']}\n\n"

        briefing += "💰 Financial Overview:\n"
        finance = yesterday_report['finance']
        briefing += f"• Daily Net: ${finance['net_daily']:.2f}\n"
        briefing += f"• Transactions: {len(finance['transactions'])}\n\n"

        briefing += "🎯 Today's Plan:\n"
        for agent, tasks in today_plan['planned_activities'].items():
            briefing += f"• {agent}: {', '.join(tasks)}\n"

        briefing += "\n🎯 Goals:\n"
        for goal in today_plan['goals']:
            briefing += f"• {goal}\n"

        return briefing

    def _get_status(self) -> str:
        """Get system status."""
        status = f"Jarvis Status:\nActive agents: {len(self.agents)}\n"
        for agent in self.agents:
            status += f"- {agent.name}: {agent.status}\n"
        return status