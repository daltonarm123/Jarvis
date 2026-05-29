"""Registry for social platform connectors."""

from __future__ import annotations

from typing import Dict, List

from .base import PlatformConnector
from .meta import MetaGraphConnector
from .tiktok import TikTokConnector
from .youtube import YouTubeConnector

_CONNECTORS: Dict[str, PlatformConnector] = {}

for connector in [MetaGraphConnector(), YouTubeConnector(), TikTokConnector()]:
    for platform in connector.platforms:
        _CONNECTORS[platform] = connector


def get_connector(platform: str) -> PlatformConnector:
    platform_key = platform.strip().lower()
    if platform_key not in _CONNECTORS:
        raise KeyError(f"Unknown platform '{platform}'. Available: {sorted(_CONNECTORS)}")
    return _CONNECTORS[platform_key]


def get_connector_for_platform(platform: str) -> PlatformConnector:
    return get_connector(platform)


def available_platforms() -> List[str]:
    return sorted(_CONNECTORS)
