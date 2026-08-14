"""Behavioral contracts for completion-driven arq shutdown waiting."""

import asyncio
import contextlib
from time import time

from arq.worker import Worker


async def _job(_ctx):
    return None


def _worker():
    return Worker([_job], handle_signals=False)


class _Pipeline:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc_info):
        return None

    async def watch(self, _key):
        return None

    async def exists(self, _key):
        return False

    async def zscore(self, _queue, _job_id):
        return int(time() * 1000)

    def multi(self):
        return None

    def psetex(self, *_args):
        return None

    async def execute(self):
        return []


class _Pool:
    def pipeline(self, *, transaction):
        assert transaction is True
        return _Pipeline()


def _production_worker(releases):
    worker = _worker()
    worker._pool = _Pool()
    worker.allow_pick_jobs = False
    worker.allow_abort_jobs = False

    async def controlled_job(job_id, _score):
        await releases[job_id].wait()

    async def no_heartbeat():
        return None

    worker.run_job = controlled_job
    worker.heart_beat = no_heartbeat
    return worker


def test_waiter_tracks_late_jobs_until_the_live_mapping_is_drained():
    async def scenario():
        releases = {"first": asyncio.Event(), "second": asyncio.Event()}
        worker = _production_worker(releases)
        await worker.start_jobs([b"first"])

        waiter = asyncio.create_task(worker._sleep_until_tasks_complete())
        await asyncio.sleep(0)
        assert not waiter.done()

        await worker.start_jobs([b"second"])
        releases["first"].set()
        await worker.tasks["first"]
        await worker._poll_iteration()
        await asyncio.sleep(0.02)
        assert not waiter.done(), "a job added after waiting began was ignored"

        releases["second"].set()
        await worker.tasks["second"]
        await asyncio.sleep(0.02)
        assert not waiter.done(), "the live task mapping was not authoritative"

        await worker._poll_iteration()
        await asyncio.wait_for(waiter, 0.2)

    asyncio.run(scenario())


def test_cancelling_the_waiter_does_not_cancel_observed_jobs():
    async def scenario():
        releases = {"job": asyncio.Event()}
        worker = _production_worker(releases)
        await worker.start_jobs([b"job"])
        job = worker.tasks["job"]

        waiter = asyncio.create_task(worker._sleep_until_tasks_complete())
        await asyncio.sleep(0)
        waiter.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await waiter

        assert not job.cancelled(), "cancelling shutdown observation cancelled a job"
        releases["job"].set()
        await job
        await worker._poll_iteration()

    asyncio.run(scenario())


def test_empty_mapping_returns_promptly():
    async def scenario():
        worker = _worker()
        worker.tasks = {}
        await asyncio.wait_for(worker._sleep_until_tasks_complete(), 0.05)

    asyncio.run(scenario())
