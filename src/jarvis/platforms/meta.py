"""Meta Graph API connector for Instagram and Facebook."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests

from .base import PlatformConnector


GRAPH_BASE = "https://graph.facebook.com/v17.0"


class MetaGraphConnector(PlatformConnector):
    name = "meta"
    platforms = ["facebook", "instagram"]

    def is_available(self) -> bool:
        return bool(os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN") or os.getenv("INSTAGRAM_ACCESS_TOKEN"))

    def supports_account_creation(self) -> bool:
        return False

    def supports_video_posting(self) -> bool:
        return True

    def supports_text_posting(self) -> bool:
        return True

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
                "Meta Graph API cannot create a new Facebook or Instagram account automatically. "
                "Jarvis can register credentials and track the account after creation. "
                "Provide access tokens and account identifiers so the social team can post on behalf of the account."
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
        if platform == "instagram":
            return self._post_instagram_video(account, video_path, caption)
        if platform == "facebook":
            return self._post_facebook_video(account, video_path, title, caption)
        raise ValueError(f"Unsupported Meta platform: {platform}")

    def post_text(
        self,
        platform: str,
        account: Dict[str, Any],
        text: str,
        image_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        if platform == "instagram":
            return self._post_instagram_media(account, text, image_url)
        if platform == "facebook":
            return self._post_facebook_text(account, text, image_url)
        raise ValueError(f"Unsupported Meta platform: {platform}")

    def _access_token(self, account: Dict[str, Any]) -> str:
        creds = account.get("credentials", {})
        return (
            creds.get("access_token")
            or account.get("access_token")
            or os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
            or os.getenv("INSTAGRAM_ACCESS_TOKEN")
        )

    def _facebook_page_id(self, account: Dict[str, Any]) -> Optional[str]:
        creds = account.get("credentials", {})
        return creds.get("page_id") or account.get("page_id") or os.getenv("FACEBOOK_PAGE_ID")

    def _instagram_account_id(self, account: Dict[str, Any]) -> Optional[str]:
        creds = account.get("credentials", {})
        return (
            creds.get("instagram_business_account_id")
            or account.get("instagram_business_account_id")
            or os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
        )

    def _post_instagram_video(self, account: Dict[str, Any], video_path: str, caption: str) -> Dict[str, Any]:
        access_token = self._access_token(account)
        insta_id = self._instagram_account_id(account)
        if not access_token or not insta_id:
            return {"success": False, "message": "Instagram account ID or access token is missing."}

        media_resp = requests.post(
            f"{GRAPH_BASE}/{insta_id}/media",
            data={
                "video_url": video_path,
                "caption": caption,
                "access_token": access_token,
            },
            timeout=60,
        )
        media_resp.raise_for_status()
        creation_id = media_resp.json().get("id")
        if not creation_id:
            return {"success": False, "message": "Instagram media object creation failed."}

        publish_resp = requests.post(
            f"{GRAPH_BASE}/{insta_id}/media_publish",
            data={
                "creation_id": creation_id,
                "access_token": access_token,
            },
            timeout=60,
        )
        publish_resp.raise_for_status()
        return {"success": True, "platform": "instagram", "media_id": publish_resp.json().get("id")}

    def _post_facebook_video(
        self,
        account: Dict[str, Any],
        video_path: str,
        title: str,
        caption: str,
    ) -> Dict[str, Any]:
        access_token = self._access_token(account)
        page_id = self._facebook_page_id(account)
        if not access_token or not page_id:
            return {"success": False, "message": "Facebook page ID or access token is missing."}

        if not video_path.startswith("http://") and not video_path.startswith("https://"):
            return {
                "success": False,
                "message": (
                    "Facebook video posting currently requires a remote video URL. "
                    "Provide a hosted video URL instead of a local file path."
                ),
            }

        resp = requests.post(
            f"{GRAPH_BASE}/{page_id}/videos",
            data={
                "file_url": video_path,
                "title": title,
                "description": caption,
                "access_token": access_token,
            },
            timeout=120,
        )
        resp.raise_for_status()
        return {"success": True, "platform": "facebook", "video_id": resp.json().get("id")}

    def _post_instagram_media(
        self,
        account: Dict[str, Any],
        caption: str,
        image_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        access_token = self._access_token(account)
        insta_id = self._instagram_account_id(account)
        if not access_token or not insta_id:
            return {"success": False, "message": "Instagram account ID or access token is missing."}

        payload = {
            "caption": caption,
            "access_token": access_token,
        }
        if image_url:
            payload["image_url"] = image_url

        create_resp = requests.post(
            f"{GRAPH_BASE}/{insta_id}/media",
            data=payload,
            timeout=60,
        )
        create_resp.raise_for_status()
        creation_id = create_resp.json().get("id")
        if not creation_id:
            return {"success": False, "message": "Instagram media creation failed."}

        publish_resp = requests.post(
            f"{GRAPH_BASE}/{insta_id}/media_publish",
            data={
                "creation_id": creation_id,
                "access_token": access_token,
            },
            timeout=60,
        )
        publish_resp.raise_for_status()
        return {"success": True, "platform": "instagram", "media_id": publish_resp.json().get("id")}

    def _post_facebook_text(
        self,
        account: Dict[str, Any],
        text: str,
        image_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        access_token = self._access_token(account)
        page_id = self._facebook_page_id(account)
        if not access_token or not page_id:
            return {"success": False, "message": "Facebook page ID or access token is missing."}

        data = {
            "message": text,
            "access_token": access_token,
        }
        if image_url:
            data["attached_media"] = [{"media_fbid": image_url}]

        resp = requests.post(
            f"{GRAPH_BASE}/{page_id}/feed",
            data=data,
            timeout=60,
        )
        resp.raise_for_status()
        return {"success": True, "platform": "facebook", "post_id": resp.json().get("id")}
