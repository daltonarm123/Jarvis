"""Scheduler tests. No API keys required."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from jarvis.scheduler import (
    Scheduler, CronSchedule, IntervalSchedule, AtSchedule, Schedule,
)


# ---------- schedule unit tests ----------

def test_cron_daily_at_9():
    s = CronSchedule("0 9 * * *")
    base = datetime(2026, 1, 1, 8, 30, tzinfo=timezone.utc)
    nxt = s.next_after(base)
    assert nxt.hour == 9 and nxt.minute == 0 and nxt.day == 1


def test_cron_shorthand_at():
    s = CronSchedule("@daily 09:30")
    base = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    nxt = s.next_after(base)
    assert nxt.day == 2 and nxt.hour == 9 and nxt.minute == 30


def test_interval_basic():
    s = IntervalSchedule(seconds=300)
    base = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    nxt = s.next_after(base)
    assert (nxt - base).total_seconds() == 300


def test_interval_with_anchor():
    anchor = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
    s = IntervalSchedule(seconds=3600, anchor=anchor)
    base = datetime(2026, 1, 1, 9, 30, tzinfo=timezone.utc)
    nxt = s.next_after(base)
    assert nxt.hour == 10 and nxt.minute == 0


def test_at_one_shot():
    when = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    s = AtSchedule(when=when)
    assert s.next_after(datetime(2026, 5, 1, tzinfo=timezone.utc)) == when
    assert s.next_after(datetime(2026, 7, 1, tzinfo=timezone.utc)) is None


def test_schedule_serialize_roundtrip():
    for s in [
        CronSchedule("0 9 * * *"),
        IntervalSchedule(seconds=60),
        AtSchedule(when=datetime(2026, 1, 1, tzinfo=timezone.utc)),
    ]:
        data = s.serialize()
        reloaded = Schedule.deserialize(data)
        assert type(reloaded).__name__ == type(s).__name__


# ---------- scheduler integration ----------

@pytest.mark.asyncio
async def test_scheduler_runs_job(tmp_path):
    counter = {"n": 0}

    async def handler(kind, payload):
        counter["n"] += 1
        return f"ran {payload.get('input')}"

    sched = Scheduler(tmp_path / "s.db", handler=handler, tick_sleep_seconds=0.05)
    await sched.start()
    try:
        # Schedule a one-shot 0.5s out
        when = datetime.now(timezone.utc) + timedelta(seconds=0.5)
        sched.add_job(
            job_id="t1", name="t1", kind="agent_task",
            payload={"input": "hello"}, schedule=AtSchedule(when=when),
        )
        await asyncio.sleep(1.5)
        assert counter["n"] == 1
        runs = sched.recent_runs("t1")
        assert len(runs) == 1 and runs[0].status == "ok"
    finally:
        await sched.stop()


@pytest.mark.asyncio
async def test_scheduler_run_now(tmp_path):
    async def handler(kind, payload):
        return "fired"

    sched = Scheduler(tmp_path / "s.db", handler=handler)
    await sched.start()
    try:
        far_future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        sched.add_job(
            job_id="x", name="x", kind="agent_task",
            payload={"input": "x"}, schedule=AtSchedule(when=far_future),
        )
        run = await sched.run_now("x")
        assert run.status == "ok" and run.output == "fired"
    finally:
        await sched.stop()


@pytest.mark.asyncio
async def test_scheduler_disables_after_max_failures(tmp_path):
    async def handler(kind, payload):
        raise RuntimeError("boom")

    sched = Scheduler(tmp_path / "s.db", handler=handler)
    await sched.start()
    try:
        sched.add_job(
            job_id="bad", name="bad", kind="agent_task",
            payload={}, schedule=IntervalSchedule(seconds=999),
            max_failures=2,
        )
        for _ in range(3):
            try:
                await sched.run_now("bad")
            except Exception:
                pass
        job = sched.get_job("bad")
        assert job.failure_count >= 2
        assert not job.enabled
    finally:
        await sched.stop()


@pytest.mark.asyncio
async def test_scheduler_persists_across_restart(tmp_path):
    async def handler(kind, payload):
        return "ok"

    db = tmp_path / "s.db"
    sched = Scheduler(db, handler=handler)
    sched.add_job(
        job_id="persist", name="persist", kind="agent_task",
        payload={"input": "x"},
        schedule=CronSchedule("0 9 * * *"),
    )
    await sched.start(); await sched.stop()

    sched2 = Scheduler(db, handler=handler)
    job = sched2.get_job("persist")
    assert job is not None
    assert job.kind == "agent_task"
    assert isinstance(job.schedule, CronSchedule)
    await sched2.start(); await sched2.stop()
