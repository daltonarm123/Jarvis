"""Schedule types — when does a job run?"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Optional


class Schedule(ABC):
    @abstractmethod
    def next_after(self, after: datetime) -> Optional[datetime]:
        """Return the next run time strictly after `after`, or None if never again."""
        ...

    @abstractmethod
    def serialize(self) -> dict: ...

    @staticmethod
    def deserialize(data: dict) -> "Schedule":
        kind = data["kind"]
        if kind == "cron":
            return CronSchedule(data["expr"])
        if kind == "interval":
            return IntervalSchedule(seconds=data["seconds"], anchor=_iso(data.get("anchor")))
        if kind == "at":
            return AtSchedule(when=_iso(data["when"]))
        raise ValueError(f"Unknown schedule kind: {kind}")


def _iso(s: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(s) if s else None


# ---------- AtSchedule (one-shot) ----------

@dataclass
class AtSchedule(Schedule):
    when: datetime

    def next_after(self, after: datetime) -> Optional[datetime]:
        if self.when > after:
            return self.when
        return None

    def serialize(self) -> dict:
        return {"kind": "at", "when": self.when.isoformat()}


# ---------- IntervalSchedule (every N seconds) ----------

@dataclass
class IntervalSchedule(Schedule):
    seconds: float
    anchor: Optional[datetime] = None  # if set, runs land on anchor + N*seconds

    def next_after(self, after: datetime) -> Optional[datetime]:
        if self.seconds <= 0:
            return None
        anchor = self.anchor or after
        if anchor > after:
            return anchor
        delta = (after - anchor).total_seconds()
        steps = int(delta // self.seconds) + 1
        return anchor + timedelta(seconds=steps * self.seconds)

    def serialize(self) -> dict:
        return {
            "kind": "interval",
            "seconds": self.seconds,
            "anchor": self.anchor.isoformat() if self.anchor else None,
        }


# ---------- CronSchedule (cron-like, simplified) ----------

# Supports the standard 5-field cron: minute hour day-of-month month day-of-week
# Plus shorthand: "@daily 09:00", "@hourly", "@every 30m"
class CronSchedule(Schedule):
    def __init__(self, expr: str) -> None:
        self.expr = expr.strip()
        self._parsed = self._parse(self.expr)

    def serialize(self) -> dict:
        return {"kind": "cron", "expr": self.expr}

    def next_after(self, after: datetime) -> Optional[datetime]:
        # Brute-force search minute-by-minute up to a year out.
        # Good enough; cron doesn't fire faster than once/min.
        candidate = (after.replace(second=0, microsecond=0) + timedelta(minutes=1))
        end = candidate + timedelta(days=366)
        while candidate < end:
            if self._matches(candidate):
                return candidate
            candidate += timedelta(minutes=1)
        return None

    # --- parsing ---

    def _parse(self, expr: str) -> dict:
        e = expr.strip()
        # Shorthands
        if e.startswith("@daily"):
            # "@daily 09:00"
            parts = e.split()
            t = parts[1] if len(parts) > 1 else "00:00"
            hh, mm = (int(x) for x in t.split(":"))
            return {"min": [mm], "hour": [hh], "dom": None, "mon": None, "dow": None}
        if e == "@hourly":
            return {"min": [0], "hour": None, "dom": None, "mon": None, "dow": None}
        if e == "@daily":
            return {"min": [0], "hour": [0], "dom": None, "mon": None, "dow": None}
        if e == "@weekly":
            return {"min": [0], "hour": [0], "dom": None, "mon": None, "dow": [0]}

        m = re.match(r"@every\s+(\d+)([smhd])", e)
        if m:
            # @every 30m → translate to interval; reject here so caller can switch.
            raise ValueError("Use IntervalSchedule for @every expressions.")

        fields = e.split()
        if len(fields) != 5:
            raise ValueError(f"Cron expr needs 5 fields, got {len(fields)}: {expr!r}")
        return {
            "min": _parse_field(fields[0], 0, 59),
            "hour": _parse_field(fields[1], 0, 23),
            "dom": _parse_field(fields[2], 1, 31),
            "mon": _parse_field(fields[3], 1, 12),
            "dow": _parse_field(fields[4], 0, 6),
        }

    def _matches(self, dt: datetime) -> bool:
        p = self._parsed
        if p["min"] is not None and dt.minute not in p["min"]:
            return False
        if p["hour"] is not None and dt.hour not in p["hour"]:
            return False
        if p["dom"] is not None and dt.day not in p["dom"]:
            return False
        if p["mon"] is not None and dt.month not in p["mon"]:
            return False
        if p["dow"] is not None and (dt.weekday() % 7) not in [d % 7 for d in p["dow"]]:
            # Python: Mon=0..Sun=6. Cron: Sun=0..Sat=6. We accept both for simple cases
            # by also matching the alternate convention.
            alt = (dt.isoweekday() % 7)  # Sun=0..Sat=6
            if alt not in [d % 7 for d in p["dow"]]:
                return False
        return True


def _parse_field(field: str, lo: int, hi: int):
    """Return None for '*', else a list of allowed values in [lo, hi]."""
    if field == "*":
        return None
    values = set()
    for part in field.split(","):
        if "/" in part:
            base, step = part.split("/")
            step = int(step)
        else:
            base, step = part, 1
        if base == "*":
            rng = range(lo, hi + 1)
        elif "-" in base:
            a, b = (int(x) for x in base.split("-"))
            rng = range(a, b + 1)
        else:
            rng = [int(base)]
        for v in rng:
            if lo <= v <= hi and (v - (lo if "-" not in base and base != "*" else min(rng))) % step == 0:
                values.add(v)
    return sorted(values)
