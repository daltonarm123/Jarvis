"""User interface for Jarvis communication."""

import asyncio


class UserInterface:
    """Handles user input and output."""

    async def get_input(self) -> str:
        """Get input from the user."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, "Jarvis> ")

    async def send_output(self, message: str):
        """Send output to the user."""
        print(message)