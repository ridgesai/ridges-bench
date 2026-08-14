"""Security and lifecycle contracts for the worker-pool control socket."""

import asyncio
import operator
import os
import socket
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from aiomisc import WorkerPool
import aiomisc.worker_pool as worker_pool_module


pytestmark = pytest.mark.skipif(not hasattr(socket, "AF_UNIX"), reason="Unix only")


def test_socket_uses_a_private_namespace_and_is_removed_after_real_work():
    async def scenario():
        pool = WorkerPool(1)
        socket_path = Path(pool.address)
        namespace = socket_path.parent

        assert socket_path.exists()
        assert not socket_path.is_symlink()
        assert stat.S_IMODE(namespace.stat().st_mode) & 0o077 == 0
        assert stat.S_IMODE(socket_path.stat().st_mode) & 0o077 == 0

        await pool.start()
        assert await pool.create_task(operator.mul, 6, 7) == 42
        await pool.close()
        await pool.close()

        assert not socket_path.exists()
        assert not namespace.exists()

    asyncio.run(scenario())


def test_failed_socket_setup_leaves_no_private_namespace(monkeypatch):
    def fail_chmod(_path, _mode):
        raise PermissionError("simulated permission failure")

    with tempfile.TemporaryDirectory(
        dir="/tmp", prefix="aiomisc-contract-"
    ) as root:
        previous_tempdir = tempfile.tempdir
        tempfile.tempdir = root
        monkeypatch.setattr(worker_pool_module, "chmod", fail_chmod)
        try:
            with pytest.raises(PermissionError, match="simulated"):
                WorkerPool(1)
        finally:
            tempfile.tempdir = previous_tempdir

        assert list(Path(root).iterdir()) == [], (
            "failed setup leaked a socket namespace"
        )


def test_non_unix_fallback_still_constructs_a_tcp_socket():
    code = r"""
import platform
import socket

platform.system = lambda: "Windows"
del socket.AF_UNIX

from aiomisc import WorkerPool

pool = WorkerPool(1)
assert pool.socket.family in (socket.AF_INET, socket.AF_INET6)
assert isinstance(pool.address, tuple) and len(pool.address) == 2
pool.socket.close()
"""
    proc = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=Path(os.environ["REPO_ROOT"]),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
