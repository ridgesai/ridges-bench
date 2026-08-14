"""Structural, Ruff, honesty, and upstream-suite verification."""

import compileall
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(os.environ["REPO_ROOT"])
RUFF_BIN = os.environ["RUFF_BIN"]
MANIFEST = Path(os.environ["BASELINE_MANIFEST"])
GATES_MODULE = Path(os.environ["GATES_MODULE"])
PREFLIGHT = Path(os.environ["PATCH_PREFLIGHT_ERROR"])
CHANGED_PATHS = Path(os.environ["CHANGED_PATHS_FILE"])
RUFF_ARGS = ["check", "--isolated", "--select", "B023", "--no-cache", "--output-format=concise"]
RUFF_SCOPE = ["procrastinate/worker.py"]
REPO_SUITE = ["tests/unit/test_worker.py"]
REPO_SUITE_ARGS = []
MIN_REPO_SUITE_PASSED = 52


def _load_gates():
    spec = importlib.util.spec_from_file_location("burndown_gates", GATES_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_submitted_patch_only_touches_declared_scope():
    error = PREFLIGHT.read_text().strip()
    assert not error, f"patch reconstruction failed: {error}"
    failures = _load_gates().submitted_path_failures(CHANGED_PATHS)
    assert not failures, "patch scope gate failed: " + "; ".join(failures)


def test_package_still_compiles():
    assert compileall.compile_dir(str(REPO_ROOT / "procrastinate"), quiet=2)


def test_targeted_ruff_findings_are_eliminated():
    proc = subprocess.run(
        [RUFF_BIN, *RUFF_ARGS, *RUFF_SCOPE],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"Ruff B023 gate failed (exit {proc.returncode}):\n"
        + proc.stdout[-3000:] + proc.stderr[-1000:]
    )


def test_fixes_are_honest():
    failures = _load_gates().check(REPO_ROOT, MANIFEST)
    assert not failures, "honesty gates failed: " + "; ".join(failures)


def test_repository_suite_still_passes():
    env = dict(os.environ)
    env.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)
    import_roots = [REPO_ROOT]
    if (REPO_ROOT / "src").is_dir():
        import_roots.insert(0, REPO_ROOT / "src")
    env["PYTHONPATH"] = os.pathsep.join(str(path) for path in import_roots)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *REPO_SUITE,
            *REPO_SUITE_ARGS,
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
            "-o",
            "addopts=",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
    )
    assert proc.returncode == 0, (
        "the repository's own suite no longer passes:\n"
        + proc.stdout[-4000:] + proc.stderr[-1500:]
    )
    match = re.search(r"(\d+) passed", proc.stdout)
    passed = int(match.group(1)) if match else 0
    assert passed >= MIN_REPO_SUITE_PASSED, (
        f"the repository suite reported only {passed} passing tests; "
        f"expected at least {MIN_REPO_SUITE_PASSED}. A skipped, deselected, "
        "or emptied suite is not evidence of preserved behavior.\n"
        + proc.stdout[-2500:]
    )
