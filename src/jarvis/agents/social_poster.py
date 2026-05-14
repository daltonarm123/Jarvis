"""Social poster agent for posting content to social media."""

from jarvis.agents.base_agent import BaseAgent


class SocialPosterAgent(BaseAgent):
    """Agent responsible for posting content to social platforms."""

    async def execute_command(self, command: str) -> str:
        """Execute posting commands."""
        if command.lower().startswith("post"):
            content = command[5:]  # Remove "post "
            return f"Posted to social media: {content}"
        elif command.lower() == "schedule post":
            return "Scheduled post for tomorrow"
        else:
            return f"Social Poster: Unknown command '{command}'"