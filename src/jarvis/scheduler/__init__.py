"""Persistent job scheduler for Jarvis.

Schedules and runs background tasks: cron-style, fixed-interval,
or one-shot. Jobs survive restarts (stored in SQLite). Misses are
detected and (optionally) caught up on next boot.

Three job kinds:
  - "agent_task"   : route input through Jarvis as if you typed it
  - "tool_call"    : call a single tool with kwargs
  - "system_event" : internal hook (used by the briefing system)
"""

from .schedules import Schedule, CronSchedule, IntervalSchedule, AtSchedule
from .scheduler import Scheduler, Job, JobRun

__all__ = [
    "Schedule",
    "CronSchedule",
    "IntervalSchedule",
    "AtSchedule",
    "Scheduler",
    "Job",
    "JobRun",
]
