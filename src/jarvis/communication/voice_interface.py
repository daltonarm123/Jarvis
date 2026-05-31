"""Voice and fallback communication layer for Jarvis."""

from __future__ import annotations

import asyncio
from typing import Optional

from .user_interface import UserInterface


class VoiceInterface:
    """A simple voice-capable interface with fallback to CLI."""

    def __init__(self) -> None:
        self.recognizer = None
        self.microphone = None
        self.tts_engine = None
        self.voice_available = False
        self._initialize_voice()

    def _initialize_voice(self) -> None:
        try:
            import speech_recognition as sr

            self.sr = sr
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            self.voice_available = True
        except Exception:
            self.sr = None
            self.microphone = None

        try:
            import pyttsx3

            self.pyttsx3 = pyttsx3
            self.tts_engine = pyttsx3.init()
            self.voice_available = True
        except Exception:
            self.pyttsx3 = None
            self.tts_engine = None

    async def get_input(self) -> str:
        if self.recognizer and self.microphone:
            text = await asyncio.to_thread(self._listen)
            if text:
                return text
        return await UserInterface().get_input()

    async def send_output(self, message: str) -> None:
        print(message)
        if self.tts_engine:
            await asyncio.to_thread(self._speak, message)

    def _listen(self) -> str:
        print("Listening for your voice command. Say something or type if voice is unavailable...")
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = self.recognizer.listen(source, timeout=8, phrase_time_limit=15)
        except Exception:
            return ""

        try:
            text = self.recognizer.recognize_google(audio)
            print(f"Heard: {text}")
            return text
        except Exception:
            return ""

    def _speak(self, message: str) -> None:
        if not self.tts_engine:
            return
        self.tts_engine.say(message)
        self.tts_engine.runAndWait()
