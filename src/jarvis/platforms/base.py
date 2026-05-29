"""Platform connector base classes and shared helpers."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


class PlatformConnector(ABC):
    name: str = "abstract"
    platforms: List[str] = []

    def is_available(self) -> bool:
        """Return True if the connector is configured and usable."""
        return False

    def supports_account_creation(self) -> bool:
        return False

    def supports_video_posting(self) -> bool:
        return False

    def supports_text_posting(self) -> bool:
        return False

    @abstractmethod
    def create_account(
        self,
        platform: str,
        alias: str,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a new account or register the account details."""

    @abstractmethod
    def post_video(
        self,
        platform: str,
        account: Dict[str, Any],
        video_path: str,
        title: str,
        caption: str,
        tags: List[str],
    ) -> Dict[str, Any]:
        """Publish a video through this platform."""

    @abstractmethod
    def post_text(
        self,
        platform: str,
        account: Dict[str, Any],
        text: str,
        image_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Publish a text or image-based post through this platform."""

    def _load_file(self, path: str) -> Tuple[Optional[bytes], Optional[str]]:
        if not path:
            return None, None
        resolved = Path(path)
        if resolved.exists():
            return resolved.read_bytes(), resolved.name
        if path.startswith("http://") or path.startswith("https://"):
            resp = requests.get(path, timeout=30)
            resp.raise_for_status()
            filename = path.rsplit("/", 1)[-1] or "media"
            return resp.content, filename
        return None, None
