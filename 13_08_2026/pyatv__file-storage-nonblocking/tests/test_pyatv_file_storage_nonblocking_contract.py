"""Behavior contracts for non-blocking FileStorage.load."""

import asyncio
import builtins
import io
import json
import os
import sys
import threading
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))
REPO_ROOT = Path(os.environ["REPO_ROOT"])
sys.path.insert(0, str(REPO_ROOT))

from pyatv.exceptions import SettingsError
from pyatv.storage.file_storage import FileStorage


def _run_load(filename):
    async def run():
        storage = FileStorage(str(filename), asyncio.get_running_loop())
        await storage.load()
        return storage

    return asyncio.run(run())


def _same_file(candidate, expected):
    try:
        return os.path.abspath(os.fspath(candidate)) == os.path.abspath(os.fspath(expected))
    except TypeError:
        return False


def test_all_target_file_operations_are_off_the_event_loop_thread(monkeypatch, tmp_path):
    owner_thread = threading.get_ident()
    calls = []
    filename = tmp_path / "storage.json"
    filename.write_text(json.dumps({"version": 1, "devices": []}), encoding="utf-8")

    original_stat = os.stat
    original_open = builtins.open
    original_io_open = io.open

    def stat(path, *args, **kwargs):
        if _same_file(path, filename):
            calls.append(("stat", threading.get_ident()))
        return original_stat(path, *args, **kwargs)

    def open_file(path, *args, **kwargs):
        if _same_file(path, filename):
            calls.append(("open", threading.get_ident()))
        return original_open(path, *args, **kwargs)

    def io_open_file(path, *args, **kwargs):
        if _same_file(path, filename):
            calls.append(("open", threading.get_ident()))
        return original_io_open(path, *args, **kwargs)

    monkeypatch.setattr(os, "stat", stat)
    monkeypatch.setattr(builtins, "open", open_file)
    monkeypatch.setattr(io, "open", io_open_file)

    storage = _run_load(filename)
    assert list(storage.settings) == []
    assert any(name == "open" for name, _ in calls), "the target file was not read"
    assert all(thread_id != owner_thread for _, thread_id in calls)


def test_missing_file_is_a_no_op(tmp_path):
    storage = _run_load(tmp_path / "missing.json")
    assert list(storage.settings) == []


def test_loaded_hash_uses_the_raw_file_data(tmp_path):
    raw = {"version": 1, "devices": []}
    filename = tmp_path / "storage.json"
    filename.write_text(json.dumps(raw), encoding="utf-8")
    storage = _run_load(filename)
    assert list(storage.settings) == []
    assert storage.has_changed(raw) is False


def test_json_parsing_failures_are_not_swallowed(tmp_path):
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        _run_load(invalid)


@pytest.mark.parametrize(
    ("raw", "error_type"),
    [
        ({"version": 1}, ValidationError),
        ({"version": 2, "devices": []}, SettingsError),
    ],
)
def test_model_validation_failures_are_not_swallowed(tmp_path, raw, error_type):
    invalid = tmp_path / "invalid-model.json"
    invalid.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(error_type):
        _run_load(invalid)


def test_read_io_failures_are_not_swallowed(monkeypatch, tmp_path):
    filename = tmp_path / "failed.json"
    filename.write_text("placeholder", encoding="utf-8")
    error = PermissionError("denied")
    original_open = builtins.open
    original_io_open = io.open

    def open_file(path, *args, **kwargs):
        if _same_file(path, filename):
            raise error
        return original_open(path, *args, **kwargs)

    def io_open_file(path, *args, **kwargs):
        if _same_file(path, filename):
            raise error
        return original_io_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", open_file)
    monkeypatch.setattr(io, "open", io_open_file)
    with pytest.raises(PermissionError, match="denied"):
        _run_load(filename)
