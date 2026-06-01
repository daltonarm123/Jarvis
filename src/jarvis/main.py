#!/usr/bin/env python3
"""Main entry point for Jarvis."""

import argparse
import asyncio
import os

from dotenv import load_dotenv

from jarvis.communication.user_interface import UserInterface
from jarvis.communication.voice_interface import VoiceInterface
from jarvis.core.jarvis_core import JarvisCore


def main() -> None:
    """Main function to run Jarvis."""
    load_dotenv()

    parser = argparse.ArgumentParser(description="Jarvis AI personal manager")
    parser.add_argument("--autonomous", action="store_true", help="Run Jarvis in autonomous mode")
    parser.add_argument("--simulate", action="store_true", help="Enable simulated posting for testing")
    parser.add_argument("--pipeline", action="store_true", help="Run a one-shot content pipeline")
    parser.add_argument("--platform", type=str, help="Target social platform for the pipeline")
    parser.add_argument("--alias", type=str, help="Social account alias for the pipeline")
    parser.add_argument("--topic", type=str, help="Topic or niche to research for the pipeline")
    parser.add_argument("--when", type=str, default="now", help="Schedule time for the pipeline publish")
    parser.add_argument("--video-path", type=str, default="", help="Local file or public URL for the video")
    parser.add_argument("--tag", action="append", default=[], help="Hashtag values for scheduled publishing")
    parser.add_argument("--ui", choices=["cli", "voice"], default="cli", help="Select the user interface")
    args = parser.parse_args()

    if args.autonomous:
        os.environ["JARVIS_MODE"] = "autonomous"
    if args.simulate:
        os.environ["JARVIS_SIMULATE_POSTING"] = "true"

    print("Starting Jarvis...")
    jarvis = JarvisCore()

    if args.pipeline:
        if not args.platform or not args.topic:
            parser.error("--pipeline requires --platform and --topic")
        result = asyncio.run(
            jarvis.run_pipeline(
                platform=args.platform,
                alias=args.alias,
                topic=args.topic,
                when=args.when,
                video_path=args.video_path,
                tags=args.tag,
            )
        )
        print(result)
        return

    if args.ui == "voice":
        ui = VoiceInterface()
        print("Voice mode enabled. Speak to Jarvis or type if voice is unavailable.")
    else:
        ui = UserInterface()

    asyncio.run(jarvis.run(ui))


if __name__ == "__main__":
    main()
