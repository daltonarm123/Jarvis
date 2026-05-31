#!/usr/bin/env python3
"""Main entry point for Jarvis."""

import asyncio
import os

from dotenv import load_dotenv

from jarvis.communication.user_interface import UserInterface
from jarvis.communication.voice_interface import VoiceInterface
from jarvis.core.jarvis_core import JarvisCore


def main() -> None:
    """Main function to run Jarvis."""
    load_dotenv()

    print("Starting Jarvis...")
    jarvis = JarvisCore()
    ui_mode = os.getenv("JARVIS_UI", "cli").lower()
    if ui_mode == "voice":
        ui = VoiceInterface()
        print("Voice mode enabled. Speak to Jarvis or type if voice is unavailable.")
    else:
        ui = UserInterface()

    asyncio.run(jarvis.run(ui))


if __name__ == "__main__":
    main()
