#!/usr/bin/env python3
"""Main entry point for Jarvis."""

import asyncio
import sys
from jarvis.core.jarvis_core import JarvisCore


def main():
    """Main function to run Jarvis."""
    print("Starting Jarvis...")

    # Initialize Jarvis core
    jarvis = JarvisCore()

    # For now, run a simple loop
    asyncio.run(jarvis.run())


if __name__ == "__main__":
    main()