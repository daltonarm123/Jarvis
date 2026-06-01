"""Simple CLI helpers to initiate OAuth flows and exchange codes.

This script is intentionally minimal: it builds an authorization URL,
prints it for the user to visit, accepts the authorization `code` pasted
back into the terminal, exchanges it for tokens, and saves the tokens to
`~/.jarvis_tokens.json` under a top-level key for the platform.

Usage examples:
  python -m jarvis.cli.oauth_cli youtube --client-id ... --client-secret ... --redirect-uri http://localhost:8080/

This file is not imported by the application at runtime unless you run it
explicitly; it avoids adding web frameworks to the codebase while giving
you a way to complete OAuth flows and persist returned tokens.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict

from jarvis.utils import oauth


TOKENS_PATH = Path.home() / ".jarvis_tokens.json"


def save_tokens(platform: str, data: Dict[str, str]) -> None:
    tokens = {}
    if TOKENS_PATH.exists():
        try:
            tokens = json.loads(TOKENS_PATH.read_text())
        except Exception:
            tokens = {}
    tokens[platform] = data
    TOKENS_PATH.write_text(json.dumps(tokens, indent=2))


def handle_youtube(args: argparse.Namespace) -> None:
    client_id = args.client_id
    client_secret = args.client_secret
    redirect_uri = args.redirect_uri
    scope = args.scope or "https://www.googleapis.com/auth/youtube.upload"
    url = oauth.build_google_oauth_url(client_id, redirect_uri, scope)
    print("Visit the following URL in your browser to authorize:")
    print(url)
    code = input("Paste the authorization code here: ").strip()
    token_json = oauth.exchange_google_code_for_token(code, client_id, client_secret, redirect_uri)
    save_tokens("youtube", token_json)
    print("Tokens saved to:", TOKENS_PATH)


def handle_facebook(args: argparse.Namespace) -> None:
    client_id = args.client_id
    client_secret = args.client_secret
    redirect_uri = args.redirect_uri
    scope = args.scope or "pages_manage_posts,pages_read_engagement"
    url = oauth.build_facebook_oauth_url(client_id, redirect_uri, scope)
    print("Visit the following URL in your browser to authorize:")
    print(url)
    code = input("Paste the authorization code here: ").strip()
    token_json = oauth.exchange_facebook_code_for_token(code, client_id, client_secret, redirect_uri)
    save_tokens("facebook", token_json)
    print("Tokens saved to:", TOKENS_PATH)


def main() -> None:
    parser = argparse.ArgumentParser(description="Jarvis OAuth helper CLI")
    sub = parser.add_subparsers(dest="cmd")

    y = sub.add_parser("youtube")
    y.add_argument("--client-id", required=True)
    y.add_argument("--client-secret", required=True)
    y.add_argument("--redirect-uri", required=True)
    y.add_argument("--scope", required=False)
    y.set_defaults(func=handle_youtube)

    f = sub.add_parser("facebook")
    f.add_argument("--client-id", required=True)
    f.add_argument("--client-secret", required=True)
    f.add_argument("--redirect-uri", required=True)
    f.add_argument("--scope", required=False)
    f.set_defaults(func=handle_facebook)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
