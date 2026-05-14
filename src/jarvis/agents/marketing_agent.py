"""Marketing agent for promoting products and content."""

from jarvis.agents.base_agent import BaseAgent


class MarketingAgent(BaseAgent):
    """Agent responsible for marketing and promotion strategies."""

    async def execute_command(self, command: str) -> str:
        """Execute marketing commands."""
        if command.lower() == "create campaign":
            return "Created marketing campaign: 'Summer Sale Extravaganza'"
        elif command.lower().startswith("analyze audience"):
            platform = command[16:]  # Remove "analyze audience "
            return f"Audience analysis for {platform}: 18-34 year olds, tech-savvy"
        elif command.lower() == "report issue":
            issue = "Ad spend not converting to sales"
            solution = await self._report_issue_to_jarvis(issue)
            return f"Reported issue to Jarvis: {issue}. Suggested solution: {solution}"
        else:
            return f"Marketing Agent: Unknown command '{command}'"

    async def _report_issue_to_jarvis(self, issue: str):
        """Report an issue to Jarvis."""
        if self.jarvis:
            solution = await self.jarvis.report_issue(self.name, issue)
            return solution
        else:
            print(f"[AGENT REPORT] {self.name}: {issue}")
            return "No Jarvis connection"