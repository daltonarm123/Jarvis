"""Stream clipper agent for clipping streamer content."""

from jarvis.agents.base_agent import BaseAgent


class StreamClipperAgent(BaseAgent):
    """Agent responsible for clipping streamer content."""

    async def execute_command(self, command: str) -> str:
        """Execute clipping commands."""
        if command.lower().startswith("clip"):
            stream_url = command[5:]  # Remove "clip "
            return f"Clipped content from: {stream_url}"
        elif command.lower() == "list clips":
            return "Available clips: clip1.mp4, clip2.mp4"
        else:
            return f"Stream Clipper: Unknown command '{command}'"