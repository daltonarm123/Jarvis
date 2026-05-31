"""TikTok connector stub with optional Business API support."""

from __future__ import annotations

import os
from typing import Any, Dict, List

import requests

from .base import PlatformConnector


class TikTokConnector(PlatformConnector):
    name = "tiktok"
    platforms = ["tiktok"]

    def is_available(self) -> bool:
        return bool(os.getenv("TIKTOK_ACCESS_TOKEN") or os.getenv("TIKTOK_CLIENT_KEY"))

    def supports_account_creation(self) -> bool:
        return False

    def supports_video_posting(self) -> bool:
        return bool(os.getenv("TIKTOK_ACCESS_TOKEN"))

    def supports_text_posting(self) -> bool:
        return False

    def create_account(
        self,
        platform: str,
        alias: str,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "success": False,
            "platform": platform,
            "alias": alias,
            "message": (
                "TikTok account creation is not available through the public API in this connector. "
                "Jarvis can still track account credentials and use stored access tokens to publish when available."
            ),
        }

    def post_video(
        self,
        platform: str,
        account: Dict[str, Any],
        video_path: str,
        title: str,
        caption: str,
        tags: List[str],
    ) -> Dict[str, Any]:
        if not self.supports_video_posting():
            return {"success": False, "message": "TikTok API credentials are not configured."}

        creds = account.get("credentials", {})
        access_token = creds.get("access_token") or account.get("access_token") or os.getenv("TIKTOK_ACCESS_TOKEN")
        username = account.get("username") or account.get("handle")
        if not access_token or not username:
            return {"success": False, "message": "TikTok access token or account handle is missing."}

        if not (video_path.startswith("http://") or video_path.startswith("https://")):
            if not os.path.exists(video_path):
                return {
                    "success": False,
                    "message": (
                        "TikTok posting requires a valid local video path or a remote video URL. "
                        "Provide a correct path to an MP4 file or a public URL."
                    ),
                }

        return {
            "success": False,
            "message": (
                "TikTok posting is currently a placeholder in this release. "
                "Jarvis can still store the account and credentials, but actual upload requires a TikTok Business API integration."
            ),
        }

    def post_text(
        self,
        platform: str,
        account: Dict[str, Any],
        text: str,
        image_url: Any = None,
    ) -> Dict[str, Any]:
        return {"success": False, "message": "TikTok only supports video posting in this connector."}
