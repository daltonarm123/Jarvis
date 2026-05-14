"""Content creator agent for generating video content."""

from jarvis.agents.base_agent import BaseAgent


class ContentCreatorAgent(BaseAgent):
    """Agent responsible for creating content ideas and scripts."""

    async def execute_command(self, command: str) -> str:
        """Execute content creation commands."""
        if command.lower() == "generate idea":
            prompt = "Generate a creative content idea for a YouTube video or social media post about AI tools."
            idea = await self.call_ai(prompt)
            return f"Generated content idea: {idea}"
        elif command.lower().startswith("create script"):
            topic = command[13:]  # Remove "create script "
            prompt = f"Create a short script outline for a video about: {topic}"
            script = await self.call_ai(prompt)
            return f"Created script for topic '{topic}': {script}"
        elif command.lower() == "report issue":
            issue = "Low engagement on recent posts"
            if self.jarvis:
                solution = await self.jarvis.report_issue(self.name, issue)
                return f"Reported issue to Jarvis: {issue}. Suggested solution: {solution}"
            else:
                return f"Reported issue: {issue} (No Jarvis connection)"
        else:
            return f"Content Creator: Unknown command '{command}'"