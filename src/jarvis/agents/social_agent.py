"""Social Automation Jarvis — account creation, posting, and content distribution."""

from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List, Optional

from jarvis.agents.base_agent import BaseAgent, Capability, TaskContext
from jarvis.agents.credentials import CredentialVault, REQUIRED_CREDENTIALS, CREDENTIAL_DESCRIPTIONS
from jarvis.platforms import get_connector, available_platforms


PLATFORM_ALIASES = {
    "tiktok": "tiktok",
    "insta": "instagram",
    "instagram": "instagram",
    "fb": "facebook",
    "facebook": "facebook",
    "yt": "youtube",
    "youtube": "youtube",
}


class SocialAgent(BaseAgent):
    name = "social"
    description = "Social account automation: create/manage accounts, publish short-form videos, and manage multi-platform posting."
    provider = "openai"
    model = "gpt-4o-mini"
    system_prompt = (
        "You are Social Jarvis. Your job is to manage faceless social media accounts and publish\n"
        "short-form content across platforms like TikTok, Instagram, Facebook, and YouTube.\n"
        "You can generate account creation plans, post descriptions, hashtags, and scheduling\n"
        "instructions for multi-account workflows. You are not allowed to take action without\n"
        "explicit approval from Jarvis, the manager. Always summarize what you plan to do and\n"
        "why, then wait for managerial sign-off before posting or creating accounts."
    )

    def __init__(self) -> None:
        self.platforms = available_platforms()

    def _get_vault(self, ctx: TaskContext) -> CredentialVault:
        state = self._load_state(ctx)
        return CredentialVault(state)

    @classmethod
    def capabilities(cls) -> List[Capability]:
        return [
            Capability(
                "social_accounts",
                "Create and manage social accounts across platforms and handle posting workflows.",
                ["tiktok", "instagram", "facebook", "youtube", "account", "create account",
                 "multi-account", "manage account", "account management", "post", "upload", "publish",
                 "schedule", "reel", "shorts", "upload video", "video upload", "credentials"],
            ),
            Capability(
                "social_strategy",
                "Plan social posting, captions, hashtags, and distribution for short-form content.",
                ["caption", "hashtag", "trending", "viral", "engagement", "audience", "analytics"],
            ),
        ]

    async def handle(self, ctx: TaskContext) -> str:
        text = ctx.user_input.strip().lower()
        if "create account" in text or "new account" in text:
            return await self._handle_account_creation(ctx)
        if "add credentials" in text or "update credentials" in text or self._looks_like_credential_input(text):
            return await self._handle_credential_input(ctx)
        if "remove account" in text or "delete account" in text:
            return self._handle_account_removal(ctx)
        if "manage account" in text or "account details" in text or "show account" in text:
            return self._handle_account_management(ctx)
        if "list accounts" in text or "accounts" in text:
            return self._list_accounts(ctx)
        if "post" in text or "publish" in text or "upload" in text:
            return await self._handle_post_request(ctx)
        return await super().handle(ctx)

    def _looks_like_credential_input(self, text: str) -> bool:
        if "for" not in text:
            return False
        if any(keyword in text for keyword in ["access_token", "page_id", "instagram_business_account_id"]):
            return True
        return "credentials" in text or "credential" in text

    def _load_state(self, ctx: TaskContext) -> Dict[str, Any]:
        return ctx.memory.get_agent_state(self.name) or {}

    def _save_state(self, ctx: TaskContext, state: Dict[str, Any]) -> None:
        ctx.memory.set_agent_state(self.name, state)

    def _suggest_account_alias(self, ctx: TaskContext, platform: str) -> str:
        state = self._load_state(ctx)
        existing = {a.get("alias") for a in state.get("accounts", [])}
        base_alias = f"{platform}_account"
        alias = base_alias
        counter = 1
        while alias in existing:
            counter += 1
            alias = f"{base_alias}{counter}"
        return alias

    def _account_exists(self, ctx: TaskContext, platform: str, alias: str) -> bool:
        state = self._load_state(ctx)
        return any(
            a.get("platform") == platform and a.get("alias") == alias
            for a in state.get("accounts", [])
        )

    def _register_account(self, ctx: TaskContext, platform: str, alias: str, status: str = "pending") -> None:
        state = self._load_state(ctx)
        accounts = state.get("accounts", [])
        if not any(a.get("platform") == platform and a.get("alias") == alias for a in accounts):
            accounts.append(
                {
                    "platform": platform,
                    "alias": alias,
                    "status": status,
                    "notes": "",
                    "has_credentials": False,
                }
            )
            state["accounts"] = accounts
            self._save_state(ctx, state)

    def _normalize_platform(self, text: str) -> Optional[str]:
        for alias, platform in PLATFORM_ALIASES.items():
            if alias in text:
                return platform
        return None

    def _find_account(self, ctx: TaskContext, platform: str) -> Optional[Dict[str, Any]]:
        state = self._load_state(ctx)
        accounts = state.get("accounts", [])
        for account in accounts:
            if account.get("platform") == platform:
                vault = self._get_vault(ctx)
                stored_creds = vault.get(platform, account.get("alias"))
                if stored_creds:
                    account["credentials"] = stored_creds
                return account
        return None

    async def _handle_account_creation(self, ctx: TaskContext) -> str:
        text = ctx.user_input.strip().lower()
        platform = self._normalize_platform(text)
        if not platform:
            return (
                "I can help register a new social account, but I need a target platform. "
                "Please tell me whether this is TikTok, Instagram, Facebook, or YouTube."
            )

        alias_match = re.search(r"as\s+([a-zA-Z0-9_\-]+)", text, re.IGNORECASE)
        alias = alias_match.group(1) if alias_match else self._suggest_account_alias(ctx, platform)
        if self._account_exists(ctx, platform, alias):
            return (
                f"An account already exists for {platform} as '{alias}'. "
                f"Use '@social list accounts' to see registered accounts."
            )

        connector = get_connector(platform)
        result = connector.create_account(platform, alias, {})
        status = "active" if result.get("success") else "pending"
        self._register_account(ctx, platform, alias, status=status)

        prompt = self._build_credential_prompt(platform, REQUIRED_CREDENTIALS.get(platform, []))
        return (
            f"{result.get('message', 'Account registered successfully.')}\n\n"
            f"Account alias: {alias}. "
            f"Once you have the credentials ready, add them by saying: '@social add credentials for {platform} {alias}'.\n"
            f"{prompt}"
        )

    async def _handle_credential_input(self, ctx: TaskContext) -> str:
        """Parse and store credentials from user input."""
        text = ctx.user_input.strip()
        platform_match = re.search(r"for\s+(\w+)\s+(\w+)", text, re.IGNORECASE)
        if not platform_match:
            return (
                "I couldn't parse your credential input. Use format: "
                "'add credentials for <platform> <alias>' followed by the credentials."
            )

        platform = self._normalize_platform(platform_match.group(1))
        alias = platform_match.group(2)
        if not platform:
            return f"Platform '{platform_match.group(1)}' is not recognized."

        required_fields = REQUIRED_CREDENTIALS.get(platform, [])
        if not required_fields:
            return f"Platform '{platform}' is not supported."

        creds = self._extract_credentials_from_text(text, required_fields)
        missing = [f for f in required_fields if f not in creds]
        if missing:
            return (
                f"Missing credentials for {platform}: {', '.join(missing)}. "
                f"Please provide all required fields."
            )

        vault = self._get_vault(ctx)
        vault.store(platform, alias, creds)
        state = self._load_state(ctx)

        if not self._account_exists(ctx, platform, alias):
            self._register_account(ctx, platform, alias, status="active")
            state = self._load_state(ctx)

        accounts = state.get("accounts", [])
        for account in accounts:
            if account.get("platform") == platform and account.get("alias") == alias:
                account["status"] = "active"
                account["has_credentials"] = True
                account["last_activity"] = "credentials_added"
                break

        state["accounts"] = accounts
        self._save_state(ctx, state)

        return (
            f"✓ Credentials for {platform} account '{alias}' have been securely stored. "
            f"This account is now ready for posting."
        )

    def _build_credential_prompt(self, platform: str, required_fields: List[str]) -> str:
        """Generate a credential collection prompt for the user."""
        descriptions = CREDENTIAL_DESCRIPTIONS.get(platform, {})
        lines = [f"To create a {platform.title()} account, I need the following credentials:\n"]
        for field in required_fields:
            desc = descriptions.get(field, field)
            lines.append(f"  • {field}: {desc}")
        return "\n".join(lines)

    def _extract_credentials_from_text(self, text: str, required_fields: List[str]) -> Dict[str, str]:
        """Parse credentials from user input using pattern matching."""
        creds = {}
        for field in required_fields:
            patterns = [
                rf"{field}\s*[:=]\s*['\"]?([^'\"]+?)['\"]?\s*(?:\n|$)",
                rf"{field}\s*[:=]\s*([^\s]+)",
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    creds[field] = match.group(1).strip()
                    break
        return creds

    async def _handle_post_request(self, ctx: TaskContext) -> str:
        text = ctx.user_input.strip()
        platform = self._normalize_platform(text.lower())
        if not platform:
            return (
                "I can post content for TikTok, Instagram, Facebook, or YouTube, "
                "but I couldn't detect the target platform. Please specify one."
            )

        account = self._find_account(ctx, platform)
        if not account:
            return (
                f"No registered account found for {platform}. "
                f"Create or register the account first with a command like 'create account for {platform}'."
            )

        if "credentials" not in account:
            return (
                f"Account '{account.get('alias')}' for {platform} exists but has no credentials stored. "
                f"Add credentials by saying: '@social add credentials for {platform} {account.get('alias')}' "
                f"and provide the required API tokens."
            )

        connector = get_connector(platform)
        if "video" in text or "reel" in text or "short" in text:
            if not connector.supports_video_posting():
                return f"{platform.title()} does not support video posting through the configured connector."

            video_path = self._extract_media_path(text)
            if not video_path:
                return (
                    "I detected a video post request, but I need a local file path or remote video URL. "
                    "Please provide the video source in your command."
                )
            title = self._extract_title(text) or f"New {platform.title()} video"
            caption = self._extract_caption(text) or "Posted by Jarvis social automation."
            tags = self._extract_tags(text)
            result = await asyncio.to_thread(
                connector.post_video,
                platform,
                account,
                video_path,
                title,
                caption,
                tags,
            )
            return self._format_connector_result(result)

        if connector.supports_text_posting():
            text_content = self._extract_caption(text) or text
            result = await asyncio.to_thread(
                connector.post_text,
                platform,
                account,
                text_content,
                None,
            )
            return self._format_connector_result(result)

        return (
            f"{platform.title()} connector can only publish videos or requires a proper media URL/file. "
            "Please include a video request if you want to publish something."
        )

    def _format_connector_result(self, result: Dict[str, Any]) -> str:
        if not isinstance(result, dict):
            return "Social publish returned an unexpected response."
        if result.get("success"):
            details = ", ".join(
                f"{k}={v}" for k, v in result.items() if k != "success"
            )
            return f"Social publish succeeded: {details or 'done'}."
        return f"Social publish failed: {result.get('message', 'Unknown error')}"

    def _handle_account_management(self, ctx: TaskContext) -> str:
        text = ctx.user_input.strip().lower()
        platform = self._normalize_platform(text)
        if not platform:
            return "Please specify which platform account you want to inspect or manage: TikTok, Instagram, Facebook, or YouTube."

        account = self._find_account(ctx, platform)
        if not account:
            return (
                f"No registered account found for {platform}. "
                f"Use 'create account for {platform}' to add one, then store credentials."
            )

        creds_available = account.get("credentials") is not None
        lines = [
            f"Account details for {account.get('alias')} ({platform}):",
            f"  • Status: {account.get('status', 'unknown')}",
            f"  • Credentials stored: {'yes' if creds_available else 'no'}",
            f"  • Last activity: {account.get('last_activity', 'not recorded')}",
            f"  • Notes: {account.get('notes', 'none')}",
        ]
        return "\n".join(lines)

    def _handle_account_removal(self, ctx: TaskContext) -> str:
        text = ctx.user_input.strip().lower()
        platform = self._normalize_platform(text)
        if not platform:
            return "Please specify the platform account to delete. Example: 'remove account for TikTok'."

        alias_match = re.search(r"for\s+\w+\s+(\w+)", text)
        alias = alias_match.group(1) if alias_match else None
        state = self._load_state(ctx)
        accounts = state.get("accounts", [])
        remaining = []
        removed = None
        for account in accounts:
            if account.get("platform") == platform and (alias is None or account.get("alias") == alias):
                removed = account
                continue
            remaining.append(account)

        if not removed:
            return (f"No matching account found for {platform} with alias '{alias or 'any'}'.")

        state["accounts"] = remaining
        self._save_state(ctx, state)
        vault = self._get_vault(ctx)
        if alias:
            vault.delete(platform, alias)
        return f"Removed account '{removed.get('alias')}' for {platform}. Credentials were also cleared from the vault."

    def _extract_media_path(self, text: str) -> Optional[str]:
        match = re.search(r"(?:video|file|media)\s*(?:is|=|:)?\s*(https?://\S+|\S+\.(?:mp4|mov|m4v))", text, re.IGNORECASE)
        return match.group(1) if match else None

    def _extract_title(self, text: str) -> Optional[str]:
        match = re.search(r"title\s*(?:is|=|:)?\s*'([^']+)'", text, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_caption(self, text: str) -> Optional[str]:
        match = re.search(r"caption\s*(?:is|=|:)?\s*'([^']+)'", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_tags(self, text: str) -> List[str]:
        tags = re.findall(r"#([a-zA-Z0-9_]+)", text)
        return tags

    def _list_accounts(self, ctx: TaskContext) -> str:
        state = self._load_state(ctx)
        accounts = state.get("accounts", [])
        if not accounts:
            return "No social accounts are registered yet. Use 'create account for <platform>' to add one."

        vault = self._get_vault(ctx)
        lines = ["Registered social accounts:"]
        for account in accounts:
            platform = account.get("platform", "unknown")
            alias = account.get("alias", "unnamed")
            status = account.get("status", "unknown")
            has_creds = vault.get(platform, alias) is not None
            cred_status = "✓ credentials stored" if has_creds else "⚠ no credentials"
            lines.append(f"  • {alias} ({platform}) - {status} [{cred_status}]")
        return "\n".join(lines)
