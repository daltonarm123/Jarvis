"""Base class for all Jarvis agents."""

from abc import ABC, abstractmethod
from typing import Optional
import os


class BaseAgent(ABC):
    """Abstract base class for agents."""

    def __init__(self, name: str, jarvis_core=None, ai_model: str = "gpt-4"):
        self.name = name
        self.status = "idle"
        self.jarvis = jarvis_core
        self.ai_model = ai_model
        self._client = None  # lazy-initialized so the system can boot without an API key

    def _get_client(self):
        """Lazily build the OpenAI client. Raises if no key is configured."""
        if self._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "OPENAI_API_KEY is not set. Add it to your .env (see .env.example)."
                )
            # Imported here so projects without `openai` installed can still
            # import this module for type checks / non-AI commands.
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=api_key)
        return self._client

    @abstractmethod
    async def execute_command(self, command: str) -> str:
        """Execute a command and return the result."""
        ...

    async def start(self):
        """Start the agent."""
        self.status = "running"

    async def stop(self):
        """Stop the agent."""
        self.status = "stopped"

    async def call_ai(self, prompt: str, max_tokens: int = 500) -> str:
        """Call the AI model with a prompt."""
        try:
            client = self._get_client()
            response = await client.chat.completions.create(
                model=self.ai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as e:
            return f"AI Error: {e}"
