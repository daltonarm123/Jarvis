"""Task automation, scheduling, and monitoring helpers for Jarvis."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

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
