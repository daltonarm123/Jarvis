"""Base class for all Jarvis agents."""

from abc import ABC, abstractmethod
from typing import Any, Optional
import os
from openai import AsyncOpenAI


class BaseAgent(ABC):
    """Abstract base class for agents."""

    def __init__(self, name: str, jarvis_core=None, ai_model: str = "gpt-4"):
        self.name = name
        self.status = "idle"
        self.jarvis = jarvis_core
        self.ai_model = ai_model
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.name = name
        self.status = "idle"
        self.jarvis = jarvis_core

    @abstractmethod
    async def execute_command(self, command: str) -> str:
        """Execute a command and return the result."""
        pass

    async def start(self):
        """Start the agent."""
        self.status = "running"

    async def stop(self):
        """Stop the agent."""
        self.status = "stopped"

    async def call_ai(self, prompt: str) -> str:
        """Call the AI model with a prompt."""
        try:
            response = await self.client.chat.completions.create(
                model=self.ai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"AI Error: {str(e)}"