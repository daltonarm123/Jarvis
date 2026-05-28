"""Provider registry.

Providers self-register on import. Lookup is by short name
("openai", "anthropic", …).
"""

from __future__ import annotations

from typing import Dict, List

from .base import LLMProvider

_REGISTRY: Dict[str, LLMProvider] = {}


def register_provider(provider: LLMProvider) -> None:
    _REGISTRY[provider.name] = provider


def get_provider(name: str) -> LLMProvider:
    if name not in _REGISTRY:
        raise KeyError(
            f"Unknown LLM provider '{name}'. "
            f"Available: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[name]


def available_providers(only_configured: bool = False) -> List[str]:
    if only_configured:
        return sorted(n for n, p in _REGISTRY.items() if p.is_configured())
    return sorted(_REGISTRY)


# Auto-register built-in providers when the package is imported.
def _bootstrap() -> None:
    from .openai_provider import OpenAIProvider
    from .anthropic_provider import AnthropicProvider

    register_provider(OpenAIProvider())
    register_provider(AnthropicProvider())


_bootstrap()
