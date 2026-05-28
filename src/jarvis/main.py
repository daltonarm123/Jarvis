#!/usr/bin/env python3
"""Main entry point for Jarvis."""

import asyncio

from dotenv import load_dotenv

from jarvis.core.jarvis_core import JarvisCore


def main() -> None:
    """Main function to run Jarvis."""
    # Load .env from the current working directory if present.
    load_dotenv()

    print("Starting Jarvis...")
    jarvis = JarvisCore()
    asyncio.run(jarvis.run())


if __name__ == "__main__":
    main()
