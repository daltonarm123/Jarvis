"""E-commerce agent for exploring business ideas and making money."""

from jarvis.agents.base_agent import BaseAgent


class EcommerceAgent(BaseAgent):
    """Agent responsible for e-commerce ideas and business development."""

    async def execute_command(self, command: str) -> str:
        """Execute e-commerce related commands."""
        if command.lower() == "generate business idea":
            prompt = "Generate an innovative e-commerce business idea that could make money online."
            idea = await self.call_ai(prompt)
            return f"Generated business idea: {idea}"
        elif command.lower().startswith("analyze market"):
            product = command[14:]  # Remove "analyze market "
            prompt = f"Analyze the market potential for: {product}. Include demand, competition, and opportunities."
            analysis = await self.call_ai(prompt)
            return f"Market analysis for {product}: {analysis}"
        elif command.lower() == "report issue":
            # Simulate reporting an issue to Jarvis
            issue = "Low conversion rates on product page"
            solution = await self._report_issue_to_jarvis(issue)
            return f"Reported issue to Jarvis: {issue}. Suggested solution: {solution}"
        else:
            return f"E-commerce Agent: Unknown command '{command}'"

    async def _report_issue_to_jarvis(self, issue: str):
        """Report an issue to Jarvis."""
        if self.jarvis:
            solution = await self.jarvis.report_issue(self.name, issue)
            return solution
        else:
            print(f"[AGENT REPORT] {self.name}: {issue}")
            return "No Jarvis connection"