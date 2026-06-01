"""OAuth helper utilities for common platform flows.

This module provides lightweight helpers to build authorization URLs and
exchange authorization codes for tokens. These helpers are intentionally
simple and meant to be used by higher-level CLI/web handlers or by the
`SocialAgent` when wiring OAuth flows.

Note: network calls use the `requests` library. The functions raise
exceptions from `requests` on network failures.
"""

from __future__ import annotations

import os
from typing import Dict, Optional

import requests
from urllib.parse import urlencode


def build_google_oauth_url(client_id: str, redirect_uri: str, scope: str, state: Optional[str] = None) -> str:
    base = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "prompt": "consent",
    }
    if state:
        params["state"] = state
    return f"{base}?{urlencode(params)}"


def exchange_google_code_for_token(code: str, client_id: str, client_secret: str, redirect_uri: str) -> Dict[str, str]:
    token_url = "https://oauth2.googleapis.com/token"
    resp = requests.post(
        token_url,
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def build_facebook_oauth_url(client_id: str, redirect_uri: str, scope: str, state: Optional[str] = None) -> str:
    base = "https://www.facebook.com/v17.0/dialog/oauth"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
    }
    if state:
        params["state"] = state
    return f"{base}?{urlencode(params)}"


def exchange_facebook_code_for_token(code: str, client_id: str, client_secret: str, redirect_uri: str) -> Dict[str, str]:
    token_url = "https://graph.facebook.com/v17.0/oauth/access_token"
    resp = requests.get(
        token_url,
        params={
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code,
        },
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def get_env_or_none(*names: str) -> Optional[str]:
    """Return the first environment-variable value that is set, or None."""
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return None
