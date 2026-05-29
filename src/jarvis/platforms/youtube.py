"""YouTube connector using the YouTube Data API via HTTP requests."""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from .base import PlatformConnector


class YouTubeConnector(PlatformConnector):
    name = "youtube"
    platforms = ["youtube"]

    def is_available(self) -> bool:
        return bool(os.getenv("YOUTUBE_ACCESS_TOKEN"))

    def supports_account_creation(self) -> bool:
        return False

    def supports_video_posting(self) -> bool:
        return True

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
                "YouTube account creation is not available through the API. "
                "Jarvis can track account credentials and use an OAuth access token to publish videos."
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
        creds = account.get("credentials", {})
        access_token = creds.get("access_token") or account.get("access_token") or os.getenv("YOUTUBE_ACCESS_TOKEN")
        if not access_token:
            return {"success": False, "message": "YouTube access token is missing."}

        video_file = Path(video_path)
        if not video_file.exists():
            return {"success": False, "message": "YouTube video upload requires a local file path."}

        metadata = {
            "snippet": {
                "title": title,
                "description": caption,
                "tags": tags,
            },
            "status": {
                "privacyStatus": "public",
            },
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        with video_file.open("rb") as payload_file:
            files = {
                "metadata": (None, json.dumps(metadata), "application/json; charset=UTF-8"),
                "file": (video_file.name, payload_file, "application/octet-stream"),
            }
            resp = requests.post(
                "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=multipart&part=snippet,status",
                headers=headers,
                files=files,
                timeout=300,
            )
        resp.raise_for_status()
        body = resp.json()
        return {"success": True, "platform": "youtube", "video_id": body.get("id"), "response": body}

    def post_text(
        self,
        platform: str,
        account: Dict[str, Any],
        text: str,
        image_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "success": False,
            "message": "YouTubeConnector only supports video posting at this time.",
        }
