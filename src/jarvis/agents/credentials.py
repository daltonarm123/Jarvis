"""Credential management for social accounts."""

from __future__ import annotations

from typing import Any, Dict, Optional
import base64


class CredentialVault:
    """Simple credential storage (can be upgraded to encryption later)."""

    def __init__(self, state: Dict[str, Any]):
        self.state = state
        if "credentials" not in state:
            state["credentials"] = {}

    def store(self, platform: str, alias: str, creds: Dict[str, str]) -> None:
        """Store credentials for a specific platform/account."""
        key = f"{platform}:{alias}"
        self.state["credentials"][key] = creds

    def get(self, platform: str, alias: str) -> Optional[Dict[str, str]]:
        """Retrieve credentials for a specific platform/account."""
        key = f"{platform}:{alias}"
        return self.state["credentials"].get(key)

    def delete(self, platform: str, alias: str) -> bool:
        """Remove credentials for a specific platform/account."""
        key = f"{platform}:{alias}"
        if key in self.state["credentials"]:
            del self.state["credentials"][key]
            return True
        return False

    def list_credentials(self) -> Dict[str, Dict[str, str]]:
        """List all stored credential keys (not values)."""
        return {k: {"stored": True} for k in self.state["credentials"]}


REQUIRED_CREDENTIALS = {
    "facebook": ["access_token", "page_id"],
    "instagram": ["access_token", "instagram_business_account_id"],
    "youtube": ["access_token"],
    "tiktok": ["access_token"],
}

CREDENTIAL_DESCRIPTIONS = {
    "facebook": {
        "access_token": "Facebook page access token (from Graph API)",
        "page_id": "Your Facebook page ID",
    },
    "instagram": {
        "access_token": "Instagram business account access token",
        "instagram_business_account_id": "Your Instagram business account ID",
    },
    "youtube": {
        "access_token": "YouTube OAuth 2.0 access token (from Google Cloud Console)",
    },
    "tiktok": {
        "access_token": "TikTok Business API access token",
    },
}
