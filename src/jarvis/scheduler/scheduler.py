"""Persistent async scheduler.

Persists jobs and run history to SQLite. A single background asyncio
task wakes up at the next scheduled run, dispatches it, and goes back
to sleep. Cancel-safe; survives restarts.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .schedules import Schedule


log = logging.getLogger("jarvis.scheduler")


SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,          -- agent_task | tool_call | system_event
    payload_json TEXT NOT NULL,
    schedule_json TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    next_run REAL,
    last_run REAL,
    last_status TEXT,            -- ok | error | skipped
    last_error TEXT,
    failure_count INTEGER NOT NULL DEFAULT 0,
    max_failures INTEGER NOT NULL DEFAULT 5,
    catch_up INTEGER NOT NULL DEFAULT 0,
    created REAL NOT NULL,
    updated REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_next ON jobs(enabled, next_run);

CREATE TABLE IF NOT EXISTS job_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    started REAL NOT NULL,
    finished REAL,
    status TEXT NOT NULL,
    output TEXT,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_job ON job_runs(job_id, started DESC);
"""


@dataclass
class Job:
    id: str
    name: str
    kind: str
    payload: Dict[str, Any]
    schedule: Schedule
    enabled: bool = True
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    last_status: Optional[str] = None
    last_error: Optional[str] = None
    failure_count: int = 0
    max_failures: int = 5
    catch_up: bool = False
    created: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class JobRun:
    job_id: str
    started: datetime
    finished: Optional[datetime]
    status: str
    output: Optional[str]
    error: Optional[str]


# Handler signature: async (kind, payload) -> str (output)
JobHandler = Callable[[str, Dict[str, Any]], Awaitable[str]]


class Scheduler:
    def __init__(
        self,
        db_path: str | Path,
        handler: JobHandler,
        tick_sleep_seconds: float = 1.0,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False, isolation_level=None)
        self._conn.executescript(SCHEMA)
        self.handler = handler
        self.tick_sleep = tick_sleep_seconds
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        self._wake = asyncio.Event()
        self._lock = asyncio.Lock()

    # ---------- public API ----------

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        await self._catch_up_missed()
        self._task = asyncio.create_task(self._run_loop(), name="jarvis-scheduler")

    async def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._task.cancel()
        self._conn.close()

    def add_job(
        self,
        job_id: str,
        name: str,
        kind: str,
        payload: Dict[str, Any],
        schedule: Schedule,
        enabled: bool = True,
        catch_up: bool = False,
        max_failures: int = 5,
    ) -> Job:
        assert kind in ("agent_task", "tool_call", "system_event"), kind
        now = datetime.now(timezone.utc)
        next_run = schedule.next_after(now)
        job = Job(
            id=job_id, name=name, kind=kind, payload=payload, schedule=schedule,
            enabled=enabled, next_run=next_run, catch_up=catch_up,
            max_failures=max_failures, created=now, updated=now,
        )
        self._upsert(job)
        self._wake.set()
        return job

    def remove_job(self, job_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        self._wake.set()
        return cur.rowcount > 0

    def list_jobs(self) -> List[Job]:
        rows = self._conn.execute(
            "SELECT id FROM jobs ORDER BY name"
        ).fetchall()
        return [self._load(r[0]) for r in rows]

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._load(job_id)

    def set_enabled(self, job_id: str, enabled: bool) -> bool:
        cur = self._conn.execute(
            "UPDATE jobs SET enabled = ?, updated = ? WHERE id = ?",
            (1 if enabled else 0, time.time(), job_id),
        )
        self._wake.set()
        return cur.rowcount > 0

    def recent_runs(self, job_id: str, limit: int = 20) -> List[JobRun]:
        rows = self._conn.execute(
            "SELECT started, finished, status, output, error FROM job_runs "
            "WHERE job_id = ? ORDER BY id DESC LIMIT ?",
            (job_id, limit),
        ).fetchall()
        return [
            JobRun(
                job_id=job_id,
                started=datetime.fromtimestamp(r[0], tz=timezone.utc),
                finished=datetime.fromtimestamp(r[1], tz=timezone.utc) if r[1] else None,
                status=r[2], output=r[3], error=r[4],
            ) for r in rows
        ]

    async def run_now(self, job_id: str) -> JobRun:
        """Fire a job immediately (off-schedule). Useful for testing."""
        job = self._load(job_id)
        if not job:
            raise KeyError(job_id)
        return await self._dispatch(job, scheduled_time=datetime.now(timezone.utc))

    # ---------- internals ----------

    async def _run_loop(self) -> None:
        log.info("Scheduler loop starting")
        while not self._stop.is_set():
            now = datetime.now(timezone.utc)
            due = self._fetch_due(now)
            for job in due:
                if self._stop.is_set():
                    break
                # Mark as in-flight by advancing next_run BEFORE dispatch,
                # so a slow handler doesn't double-fire on overlapping ticks.
                next_run = job.schedule.next_after(now)
                self._update_next(job.id, next_run)
                try:
                    await self._dispatch(job, scheduled_time=job.next_run or now)
                except Exception as e:  # pragma: no cover - defensive
                    log.exception("Dispatch crashed for %s: %s", job.id, e)

            # Sleep until the next job, or until woken/stopped.
            sleep_for = self._seconds_until_next(now)
            try:
                self._wake.clear()
                await asyncio.wait_for(self._wake.wait(), timeout=sleep_for)
            except asyncio.TimeoutError:
                pass
        log.info("Scheduler loop exiting")

    async def _dispatch(self, job: Job, scheduled_time: datetime) -> JobRun:
        run_id = self._begin_run(job.id, scheduled_time)
        async with self._lock:
            started = datetime.now(timezone.utc)
        try:
            output = await self.handler(job.kind, job.payload)
            finished = datetime.now(timezone.utc)
            self._finish_run(run_id, "ok", output=output, error=None)
            self._mark_success(job.id, finished)
            return JobRun(job.id, started, finished, "ok", output, None)
        except Exception as e:
            finished = datetime.now(timezone.utc)
            err = f"{type(e).__name__}: {e}"
            self._finish_run(run_id, "error", output=None, error=err)
            self._mark_failure(job.id, finished, err)
            log.warning("Job %s failed: %s", job.id, err)
            return JobRun(job.id, started, finished, "error", None, err)

    async def _catch_up_missed(self) -> None:
        """On startup, run any catch_up jobs that should have fired while we were down."""
        now = datetime.now(timezone.utc)
        rows = self._conn.execute(
            "SELECT id FROM jobs WHERE enabled = 1 AND catch_up = 1 "
            "AND next_run IS NOT NULL AND next_run < ?",
            (now.timestamp(),),
        ).fetchall()
        for (job_id,) in rows:
            job = self._load(job_id)
            if not job:
                continue
            log.info("Catch-up: running missed job %s", job_id)
            # Advance schedule past now so we don't re-catch-up on next boot.
            self._update_next(job_id, job.schedule.next_after(now))
            try:
                await self._dispatch(job, scheduled_time=now)
            except Exception:
                log.exception("Catch-up dispatch failed for %s", job_id)

    def _seconds_until_next(self, now: datetime) -> float:
        row = self._conn.execute(
            "SELECT MIN(next_run) FROM jobs WHERE enabled = 1 AND next_run IS NOT NULL"
        ).fetchone()
        if not row or row[0] is None:
            return 60.0  # idle wake every minute
        delta = max(0.5, row[0] - now.timestamp())
        return min(delta, 60.0)

    def _fetch_due(self, now: datetime) -> List[Job]:
        rows = self._conn.execute(
            "SELECT id FROM jobs WHERE enabled = 1 AND next_run IS NOT NULL AND next_run <= ?",
            (now.timestamp(),),
        ).fetchall()
        return [self._load(r[0]) for r in rows if self._load(r[0])]

    # ---------- persistence ----------

    def _upsert(self, job: Job) -> None:
        self._conn.execute(
            "INSERT INTO jobs(id, name, kind, payload_json, schedule_json, enabled, next_run, last_run, "
            " last_status, last_error, failure_count, max_failures, catch_up, created, updated) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET "
            "  name=excluded.name, kind=excluded.kind, payload_json=excluded.payload_json, "
            "  schedule_json=excluded.schedule_json, enabled=excluded.enabled, next_run=excluded.next_run, "
            "  max_failures=excluded.max_failures, catch_up=excluded.catch_up, updated=excluded.updated",
            (
                job.id, job.name, job.kind, json.dumps(job.payload),
                json.dumps(job.schedule.serialize()), 1 if job.enabled else 0,
                job.next_run.timestamp() if job.next_run else None,
                job.last_run.timestamp() if job.last_run else None,
                job.last_status, job.last_error, job.failure_count, job.max_failures,
                1 if job.catch_up else 0, job.created.timestamp(), job.updated.timestamp(),
            ),
        )

    def _load(self, job_id: str) -> Optional[Job]:
        row = self._conn.execute(
            "SELECT name, kind, payload_json, schedule_json, enabled, next_run, last_run, "
            "       last_status, last_error, failure_count, max_failures, catch_up, created, updated "
            "FROM jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        if not row:
            return None
        return Job(
            id=job_id,
            name=row[0],
            kind=row[1],
            payload=json.loads(row[2]),
            schedule=Schedule.deserialize(json.loads(row[3])),
            enabled=bool(row[4]),
            next_run=datetime.fromtimestamp(row[5], tz=timezone.utc) if row[5] else None,
            last_run=datetime.fromtimestamp(row[6], tz=timezone.utc) if row[6] else None,
            last_status=row[7],
            last_error=row[8],
            failure_count=row[9],
            max_failures=row[10],
            catch_up=bool(row[11]),
            created=datetime.fromtimestamp(row[12], tz=timezone.utc),
            updated=datetime.fromtimestamp(row[13], tz=timezone.utc),
        )

    def _update_next(self, job_id: str, next_run: Optional[datetime]) -> None:
        self._conn.execute(
            "UPDATE jobs SET next_run = ?, updated = ? WHERE id = ?",
            (next_run.timestamp() if next_run else None, time.time(), job_id),
        )

    def _mark_success(self, job_id: str, finished: datetime) -> None:
        self._conn.execute(
            "UPDATE jobs SET last_run = ?, last_status = 'ok', last_error = NULL, "
            "failure_count = 0, updated = ? WHERE id = ?",
            (finished.timestamp(), time.time(), job_id),
        )

    def _mark_failure(self, job_id: str, finished: datetime, err: str) -> None:
        row = self._conn.execute(
            "SELECT failure_count, max_failures FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
        fc = (row[0] if row else 0) + 1
        maxf = row[1] if row else 5
        disable = fc >= maxf
        self._conn.execute(
            "UPDATE jobs SET last_run = ?, last_status = 'error', last_error = ?, "
            "failure_count = ?, enabled = ?, updated = ? WHERE id = ?",
            (finished.timestamp(), err, fc, 0 if disable else 1, time.time(), job_id),
        )
        if disable:
            log.warning("Job %s disabled after %d failures", job_id, fc)

    def _begin_run(self, job_id: str, scheduled: datetime) -> int:
        cur = self._conn.execute(
            "INSERT INTO job_runs(job_id, started, status) VALUES(?, ?, 'running')",
            (job_id, scheduled.timestamp()),
        )
        return cur.lastrowid

    def _finish_run(self, run_id: int, status: str, output: Optional[str], error: Optional[str]) -> None:
        self._conn.execute(
            "UPDATE job_runs SET finished = ?, status = ?, output = ?, error = ? WHERE id = ?",
            (time.time(), status, (output or "")[:8000], (error or "")[:2000], run_id),
        )
