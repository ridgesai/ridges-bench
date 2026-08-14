"""Production-path contracts for procrastinate's per-job abort callbacks."""

import asyncio

from procrastinate.app import App
from procrastinate.job_context import AbortReason
from procrastinate.testing import InMemoryConnector
from procrastinate.worker import Worker


def test_concurrent_jobs_keep_distinct_live_abort_reason_lookups():
    async def scenario():
        app = App(connector=InMemoryConnector())
        async with app.open_async():

            @app.task(name="abort-attribution-contract", pass_context=True)
            async def contract_job(_context):
                return None

            job_ids = [await contract_job.defer_async() for _ in range(3)]
            worker = Worker(
                app,
                concurrency=3,
                wait=False,
                install_signal_handlers=False,
            )
            worker.worker_id = await app.job_manager.register_worker()
            contexts = []

            async def capture(context):
                contexts.append(context)

            worker._process_job = capture
            await worker._fetch_and_process_jobs()
            await asyncio.sleep(0)

            assert [context.job.id for context in contexts] == job_ids
            reasons = [
                AbortReason.SHUTDOWN,
                AbortReason.USER_REQUEST,
                AbortReason.SHUTDOWN,
            ]
            worker._job_ids_to_abort = dict(zip(job_ids, reasons, strict=True))
            assert [context.abort_reason() for context in contexts] == reasons

            worker._job_ids_to_abort[job_ids[0]] = AbortReason.USER_REQUEST
            del worker._job_ids_to_abort[job_ids[1]]
            assert contexts[0].abort_reason() is AbortReason.USER_REQUEST
            assert contexts[1].abort_reason() is None
            assert contexts[2].abort_reason() is AbortReason.SHUTDOWN

    asyncio.run(scenario())
