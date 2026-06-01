"""CLI to manage .env values and test integrations (IMAP check).

Usage examples:
  python -m jarvis.cli.config_cli set EMAIL_IMAP_HOST imap.example.com
  python -m jarvis.cli.config_cli test-imap
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv, set_key
import imaplib


ENV_PATH = Path(".env")

def set_env_var(key: str, value: str, env_path: Optional[Path] = None) -> None:
    env_path = env_path or ENV_PATH
    if not env_path.exists():
        env_path.write_text("")
    # use python-dotenv to set or update
    set_key(str(env_path), key, value)
    print(f"Set {key} in {env_path}")


def test_imap() -> None:
    load_dotenv()
    host = os.getenv("EMAIL_IMAP_HOST")
    port = int(os.getenv("EMAIL_IMAP_PORT", "993"))
    user = os.getenv("EMAIL_IMAP_USER")
    password = os.getenv("EMAIL_IMAP_PASSWORD")
    if not (host and user and password):
        print("EMAIL_IMAP_HOST, EMAIL_IMAP_USER and EMAIL_IMAP_PASSWORD must be set in .env or environment.")
        return
    try:
        client = imaplib.IMAP4_SSL(host, port)
        client.login(user, password)
        client.select(os.getenv("EMAIL_IMAP_FOLDER", "INBOX"))
        client.logout()
        print("IMAP connection successful.")
    except Exception as e:
        print("IMAP connection failed:", e)


def main() -> None:
    parser = argparse.ArgumentParser(description="Jarvis config helper")
    sub = parser.add_subparsers(dest="cmd")

    s = sub.add_parser("set")
    s.add_argument("key")
    s.add_argument("value")

    t = sub.add_parser("test-imap")

    args = parser.parse_args()
    if args.cmd == "set":
        set_env_var(args.key, args.value)
    elif args.cmd == "test-imap":
        test_imap()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
