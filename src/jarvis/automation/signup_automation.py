"""Scaffold for browser-based signup automation.

This module provides a non-imported helper class that demonstrates how
one could implement browser automation for account signup (e.g. TikTok).
It intentionally avoids importing heavy browser libraries at module
import time so the repository remains testable without extra deps.

To use the scaffold you will need to install a browser automation
library such as `playwright` or `selenium` and implement the concrete
selectors and flows for the target platform.
"""

from __future__ import annotations

from typing import Dict, Optional


class SignupAutomator:
    """Scaffold for performing web-based account signups.

    Example usage (conceptual):

        automator = SignupAutomator(headless=True)
        result = automator.create_account("tiktok", {
            "email": "example+alias@example.com",
            "password": "S3cureP@ssw0rd",
            "display_name": "myhandle",
        })

    The actual implementation should use Playwright or Selenium and handle
    captchas, multi-step verification, and rate-limiting according to the
    platform's terms of service.
    """

    def __init__(self, headless: bool = True, browser_path: Optional[str] = None):
        self.headless = headless
        self.browser_path = browser_path

    def create_account(self, platform: str, details: Dict[str, str]) -> Dict[str, str]:
        """Attempt to create an account for `platform` using `details`.

        Returns a dict with keys: success(bool), message(str), account_info(dict).
        This is a stub and must be implemented for each platform.
        """
        return {
            "success": False,
            "message": "Browser automation scaffold not implemented. Install Playwright or Selenium and implement this method.",
            "account_info": {},
        }

    # Helper methods for real implementations could go here, e.g.:
    # - open_browser()
    # - fill_field()
    # - handle_captcha()
    # - wait_for_selector()
