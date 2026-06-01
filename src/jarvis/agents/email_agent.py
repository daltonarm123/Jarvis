"""Email automation for creating and monitoring tracked email addresses."""

from __future__ import annotations

import email
import imaplib
import os
import re
import time
import uuid
from email.header import decode_header
from typing import Any, Dict, List, Optional

from .base_agent import BaseAgent, Capability, TaskContext

EMAIL_DOMAIN = os.getenv("JARVIS_EMAIL_DOMAIN", "jarvis.local")
EMAIL_BASE_ADDRESS = os.getenv("EMAIL_BASE_ADDRESS")
EMAIL_IMAP_HOST = os.getenv("EMAIL_IMAP_HOST")
EMAIL_IMAP_PORT = int(os.getenv("EMAIL_IMAP_PORT", "993"))
EMAIL_IMAP_USER = os.getenv("EMAIL_IMAP_USER")
EMAIL_IMAP_PASSWORD = os.getenv("EMAIL_IMAP_PASSWORD")
EMAIL_IMAP_FOLDER = os.getenv("EMAIL_IMAP_FOLDER", "INBOX")


def make_tracked_email_address(alias: str) -> str:
    cleaned_alias = re.sub(r"[^a-zA-Z0-9._+-]", "_", alias)
    base_address = EMAIL_BASE_ADDRESS or EMAIL_IMAP_USER
    if base_address and "@" in base_address:
        local, domain = base_address.split("@", 1)
        return f"{local}+{cleaned_alias}@{domain}"
    return f"{cleaned_alias}@{EMAIL_DOMAIN}"


class EmailAgent(BaseAgent):
    name = "email"
    description = (
        "Email automation: create tracked signup email addresses and monitor incoming confirmations."
    )
    provider = "openai"
    model = "gpt-4o-mini"
    system_prompt = (
        "You are Email Jarvis. You create and manage tracked email addresses for account signups, "
        "monitor inbox status, and help the manager keep track of verification workflows. "
        "If no real email provider is configured, keep the email state internally and report it clearly."
    )

    def __init__(self) -> None:
        self.real_mode = bool(
            EMAIL_IMAP_HOST
            and EMAIL_IMAP_USER
            and EMAIL_IMAP_PASSWORD
            and (EMAIL_BASE_ADDRESS or EMAIL_IMAP_USER)
        )

    @classmethod
    def capabilities(cls) -> List[Capability]:
        return [
            Capability(
                "email_management",
                "Create and monitor tracked email addresses for account signup workflows.",
                ["email", "create email", "monitor email", "inbox", "confirmation"],
            )
        ]

    async def handle(self, ctx: TaskContext) -> str:
        text = ctx.user_input.strip().lower()

        if "create email" in text or "new email" in text or "generate email" in text:
            return self._handle_email_creation(ctx)

        if "check inbox" in text or "monitor email" in text or "read email" in text:
            return self._handle_email_monitoring(ctx)

        if "list emails" in text or "show emails" in text:
            return self._list_emails(ctx)

        if "add message" in text or "inject message" in text:
            return self._handle_add_email_message(ctx)

        return (
            "I can manage tracked email addresses for signups and verification. "
            "Try: 'create email for social signup', 'check inbox for <address>', or 'list emails'."
        )

    def _get_email_state(self, ctx: TaskContext) -> Dict[str, Any]:
        return ctx.memory.get_agent_state(self.name) or {}

    def _save_email_state(self, ctx: TaskContext, state: Dict[str, Any]) -> None:
        ctx.memory.set_agent_state(self.name, state)

    def _handle_email_creation(self, ctx: TaskContext) -> str:
        alias = self._extract_alias(ctx.user_input)
        purpose = self._extract_purpose(ctx.user_input)
        address = self._create_email_address(ctx, alias=alias, purpose=purpose)
        return (
            f"Created tracked email address {address}. "
            f"Use '@email monitor {address}' to check for confirmation messages."
        )

    def _handle_email_monitoring(self, ctx: TaskContext) -> str:
        address = self._extract_address(ctx.user_input)
        if not address:
            return "Please specify the email address to monitor, for example: 'check inbox for jarvis123@domain.com'."

        email_record = self._find_email(ctx, address)
        if not email_record:
            return f"No tracked email found for {address}. Create one first with 'create email ...'."

        if self.real_mode:
            messages = self._fetch_real_messages(address)
            if not messages:
                return f"No new messages found for {address}."
            return self._format_message_list(address, messages)

        if not email_record.get("messages"):
            return f"No new messages for {address}."

        return self._format_inbox(email_record)

    def _handle_add_email_message(self, ctx: TaskContext) -> str:
        address = self._extract_address(ctx.user_input)
        if not address:
            return "Please specify the tracked email address to receive the message."

        email = self._find_email(ctx, address)
        if not email:
            return f"No tracked email found for {address}."

        subject = self._extract_subject(ctx.user_input) or "No subject"
        body = self._extract_body(ctx.user_input) or "[message body not provided]"
        email["messages"].append({
            "received": time.time(),
            "subject": subject,
            "body": body,
        })
        self._save_email_state(ctx, self._get_email_state(ctx))
        return f"Added a simulated message to {address}."

    def _list_emails(self, ctx: TaskContext) -> str:
        state = self._get_email_state(ctx)
        emails = state.get("emails", [])
        if not emails:
            return "No tracked email addresses have been created yet."

        lines = ["Tracked emails:"]
        for email in emails:
            lines.append(
                f"  • {email['address']} (purpose={email.get('purpose','general')}, status={email.get('status','active')})"
            )
        return "\n".join(lines)

    def _create_email_address(
        self,
        ctx: TaskContext,
        alias: Optional[str] = None,
        purpose: Optional[str] = None,
    ) -> str:
        state = self._get_email_state(ctx)
        emails = state.get("emails", [])
        alias = alias or f"email_{uuid.uuid4().hex[:8]}"
        address = self._generate_address(alias)
        email = {
            "address": address,
            "alias": alias,
            "purpose": purpose or "signup",
            "status": "active",
            "created": time.time(),
            "linked_account": None,
            "messages": [],
            "real_mode": self.real_mode,
        }
        emails.append(email)
        state["emails"] = emails
        self._save_email_state(ctx, state)
        return address

    def _find_email(self, ctx: TaskContext, address: str) -> Optional[Dict[str, Any]]:
        state = self._get_email_state(ctx)
        emails = state.get("emails", [])
        return next((email for email in emails if email.get("address") == address), None)

    def _generate_address(self, alias: str) -> str:
        if self.real_mode:
            return make_tracked_email_address(alias)
        domain = EMAIL_DOMAIN.strip() or "jarvis.local"
        return f"{alias}@{domain}"

    def _extract_alias(self, text: str) -> Optional[str]:
        match = re.search(r"as\s+([a-zA-Z0-9_\-]+)", text)
        return match.group(1) if match else None

    def _extract_purpose(self, text: str) -> Optional[str]:
        match = re.search(r"for\s+([a-zA-Z0-9_\- ]+)", text)
        if match:
            purpose = match.group(1).strip()
            if "email" not in purpose:
                return purpose
        return None

    def _extract_address(self, text: str) -> Optional[str]:
        match = re.search(r"([\w.+-]+@[\w.-]+\.[a-zA-Z]{2,})", text)
        return match.group(1) if match else None

    def _fetch_real_messages(self, address: str) -> List[Dict[str, Any]]:
        try:
            client = imaplib.IMAP4_SSL(EMAIL_IMAP_HOST, EMAIL_IMAP_PORT)
            client.login(EMAIL_IMAP_USER, EMAIL_IMAP_PASSWORD)
            client.select(EMAIL_IMAP_FOLDER)
            status, data = client.search(None, 'TO', f'"{address}"')
            if status != "OK":
                client.logout()
                return []
            message_ids = data[0].split()
            messages: List[Dict[str, Any]] = []
            for msg_id in message_ids[-10:]:
                status, msg_data = client.fetch(msg_id, "RFC822")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue
                raw_email = msg_data[0][1]
                parsed = email.message_from_bytes(raw_email)
                subject = self._decode_mime_header(parsed.get("Subject", "(no subject)"))
                sender = self._decode_mime_header(parsed.get("From", "unknown"))
                date = parsed.get("Date", "unknown")
                snippet = self._get_message_snippet(parsed)
                messages.append({
                    "subject": subject,
                    "from": sender,
                    "date": date,
                    "snippet": snippet,
                })
            client.logout()
            return messages
        except Exception:
            return []

    def _decode_mime_header(self, value: str) -> str:
        decoded_parts = decode_header(value)
        parts: List[str] = []
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                parts.append(part.decode(encoding or "utf-8", errors="ignore"))
            else:
                parts.append(part)
        return "".join(parts)

    def _get_message_snippet(self, msg: email.message.Message) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain" and part.get_content_disposition() != "attachment":
                    return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore").strip()[:200]
        else:
            return msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="ignore").strip()[:200]
        return ""

    def _format_message_list(self, address: str, messages: List[Dict[str, Any]]) -> str:
        lines = [f"Inbox for {address}:"]
        for msg in messages:
            lines.append(f"  • {msg['date']} from {msg['from']}: {msg['subject']}")
            lines.append(f"    {msg['snippet']}")
        return "\n".join(lines)

    def _extract_subject(self, text: str) -> Optional[str]:
        match = re.search(r"subject\s*(?:is|=|:)?\s*'([^']+)'", text)
        return match.group(1).strip() if match else None

    def _extract_body(self, text: str) -> Optional[str]:
        match = re.search(r"body\s*(?:is|=|:)?\s*'([^']+)'", text)
        return match.group(1).strip() if match else None

    def _format_inbox(self, email: Dict[str, Any]) -> str:
        lines = [f"Inbox for {email['address']}:" ]
        for msg in email.get("messages", []):
            received = time.strftime("%Y-%m-%d %H:%M", time.localtime(msg["received"]))
            lines.append(f"  - {received}: {msg['subject']}")
            lines.append(f"    {msg['body']}")
        return "\n".join(lines)
