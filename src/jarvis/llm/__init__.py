"""LLM provider abstraction.

Lets agents declare what kind of model they need (e.g. "claude-fast",
"openai-coding") without caring which vendor's API they go to. New
providers (Ollama, Gemini, Groq, …) plug in by implementing
`LLMProvider`.
"""

from .base import LLMProvider, LLMMessage, LLMResponse
from .registry import get_provider, register_provider, available_providers

__all__ = [
    "LLMProvider",
    "LLMMessage",
    "LLMResponse",
    "get_provider",
    "register_provider",
    "available_providers",
]
