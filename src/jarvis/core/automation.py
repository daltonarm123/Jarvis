"""Task automation, scheduling, and monitoring helpers for Jarvis."""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from jarvis.memory import MemoryStore


@dataclass
class TaskItem:
    agent: str
    summary: str
    status: str = "pending"
    created: float = field(default_factory=time.time)
    source: str = "daily_plan"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "summary": self.summary,
            "status": self.status,
            "created": self.created,
            "source": self.source,
        }


@dataclass
class ScheduleItem:
    id: str
    platform: str
    alias: str
    video_path: str
    title: str
    caption: str
    tags: List[str]
    scheduled_at: float
    status: str = "pending"
    created: float = field(default_factory=time.time)
    source: str = "scheduled"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform,
            "alias": self.alias,
            "video_path": self.video_path,
            "title": self.title,
            "caption": self.caption,
            "tags": self.tags,
            "scheduled_at": self.scheduled_at,
            "status": self.status,
            "created": self.created,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ScheduleItem":
        return cls(
            id=raw.get("id", ""),
            platform=raw.get("platform", ""),
            alias=raw.get("alias", ""),
            video_path=raw.get("video_path", ""),
            title=raw.get("title", ""),
            caption=raw.get("caption", ""),
            tags=raw.get("tags", []),
            scheduled_at=raw.get("scheduled_at", time.time()),
            status=raw.get("status", "pending"),
            created=raw.get("created", time.time()),
            source=raw.get("source", "scheduled"),
        )


class ScheduleManager:
    """Stores and retrieves scheduled publishing entries."""

    SCHEDULE_FACT_KEY = "scheduled_posts"

    def __init__(self, memory: MemoryStore) -> None:
        self.memory = memory

    def add_schedule(
        self,
        platform: str,
        alias: str,
        video_path: str,
        title: str,
        caption: str,
        tags: List[str],
        when: str,
    ) -> ScheduleItem:
        scheduled_at = self._parse_schedule_time(when)
        item = ScheduleItem(
            id=str(uuid.uuid4()),
            platform=platform,
            alias=alias,
            video_path=video_path,
            title=title,
            caption=caption,
            tags=tags,
            scheduled_at=scheduled_at,
        )
        entries = self.get_schedules()
        entries.append(item)
        self._save_schedules(entries)
        return item

    def get_schedules(self) -> List[ScheduleItem]:
        raw = self.memory.get_fact(self.SCHEDULE_FACT_KEY, [])
        if not isinstance(raw, list):
            return []
        schedules: List[ScheduleItem] = []
        for item in raw:
            if isinstance(item, dict) and item.get("id"):
                schedules.append(ScheduleItem.from_dict(item))
        return schedules

    def get_due_schedules(self, now: Optional[float] = None) -> List[ScheduleItem]:
        now = now or time.time()
        return [item for item in self.get_schedules() if item.status == "pending" and item.scheduled_at <= now]

    def set_schedule_status(self, schedule_id: str, status: str) -> None:
        schedules = self.get_schedules()
        for item in schedules:
            if item.id == schedule_id:
                item.status = status
        self._save_schedules(schedules)

    def remove_schedule(self, schedule_id: str) -> bool:
        schedules = self.get_schedules()
        filtered = [item for item in schedules if item.id != schedule_id]
        if len(filtered) == len(schedules):
            return False
        self._save_schedules(filtered)
        return True

    def get_schedule_summary(self) -> str:
        schedules = self.get_schedules()
        if not schedules:
            return "No scheduled posts yet. Use '/schedule add' to queue publishing."
        lines = ["Scheduled posts:"]
        for item in schedules:
            when = time.strftime("%Y-%m-%d %H:%M", time.localtime(item.scheduled_at))
            lines.append(
                f"  • {item.id}: {item.platform}/{item.alias} at {when} - {item.title} [{item.status}]"
            )
        return "\n".join(lines)

    def _save_schedules(self, schedules: List[ScheduleItem]) -> None:
        self.memory.set_fact(self.SCHEDULE_FACT_KEY, [item.to_dict() for item in schedules])

    def _parse_schedule_time(self, text: str) -> float:
        text = text.strip().lower()
        now = time.time()
        if text in ("now", "today"):
            return now
        if text == "tomorrow":
            return now + 24 * 60 * 60
        hours_match = re.search(r"in\s+(\d+)\s*hours?", text)
        if hours_match:
            return now + int(hours_match.group(1)) * 60 * 60
        days_match = re.search(r"in\s+(\d+)\s*days?", text)
        if days_match:
            return now + int(days_match.group(1)) * 24 * 60 * 60
        try:
            from datetime import datetime

            for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
                try:
                    dt = datetime.strptime(text, fmt)
                    return dt.timestamp()
                except ValueError:
                    continue
        except Exception:
            pass
        return now


class TaskMonitor:
    """Keeps track of daily tasks and exposes summaries."""

    TASK_FACT_KEY = "daily_tasks"

    def __init__(self, memory: MemoryStore) -> None:
        self.memory = memory

    def sync_tasks(self, agent_plans: Dict[str, str]) -> None:
        tasks: List[TaskItem] = []
        for agent, plan in agent_plans.items():
            tasks.extend(self._extract_tasks(agent, plan))
        self.memory.set_fact(self.TASK_FACT_KEY, [task.to_dict() for task in tasks])

    def _extract_tasks(self, agent: str, plan: str) -> List[TaskItem]:
        tasks: List[TaskItem] = []
        for line in plan.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("-") or line.startswith("•"):
                clean = re.sub(r"^[-•\s]+", "", line)
            else:
                clean = re.sub(r"^\d+[\.)]?\s*", "", line)
            clean = clean.strip()
            if not clean:
                continue
            tasks.append(TaskItem(agent=agent, summary=clean))
        return tasks

    def get_tasks(self) -> List[TaskItem]:
        raw = self.memory.get_fact(self.TASK_FACT_KEY, [])
        if not isinstance(raw, list):
            return []
        tasks: List[TaskItem] = []
        for item in raw:
            if isinstance(item, dict) and "summary" in item:
                tasks.append(TaskItem(**item))
        return tasks

    def get_task_summary(self) -> str:
        tasks = self.get_tasks()
        if not tasks:
            return "No active tasks have been created yet. Generate a briefing first with /briefing."
        agent_groups: Dict[str, List[TaskItem]] = {}
        for task in tasks:
            agent_groups.setdefault(task.agent, []).append(task)

        lines = ["Current work plan for the team:"]
        for agent, group in sorted(agent_groups.items()):
            lines.append(f"\n{agent}:")
            for task in group:
                lines.append(f"  - {task.summary} [{task.status}]")
        return "\n".join(lines)

    def overdue_text(self) -> str:
        tasks = self.get_tasks()
        if not tasks:
            return "No tasks to monitor yet."
        lines = ["Task monitoring summary:"]
        pending = [t for t in tasks if t.status == "pending"]
        lines.append(f"Pending tasks: {len(pending)}")
        return "\n".join(lines)
