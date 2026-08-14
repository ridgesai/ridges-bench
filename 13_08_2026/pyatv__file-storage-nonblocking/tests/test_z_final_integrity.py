"""Run the patch-scope and honesty checks again after all executable tests."""

import importlib.util
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(os.environ["REPO_ROOT"])
GATES_MODULE = Path(os.environ["GATES_MODULE"])
MANIFEST = Path(os.environ["BASELINE_MANIFEST"])
FINAL_PATHS = Path(os.environ["FINAL_CHANGED_PATHS_FILE"])
CANDIDATE_PATCH = Path(os.environ["CANDIDATE_PATCH_FILE"])


def _load_gates():
    spec = importlib.util.spec_from_file_location("burndown_gates_final", GATES_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_z_workspace_integrity_after_execution():
    def git(*args):
        return subprocess.run(
            ["git", "-c", f"safe.directory={REPO_ROOT}", "-C", str(REPO_ROOT), *args],
            capture_output=True,
        )

    staged = git("add", "-A", "--", ".")
    assert staged.returncode == 0, staged.stderr.decode(errors="replace")
    inventory = git("diff", "--cached", "--name-only", "-z", "HEAD")
    final_patch = git("diff", "--cached", "--binary", "--full-index", "HEAD")
    reset = git("reset", "--mixed", "--quiet", "HEAD")
    assert inventory.returncode == 0, inventory.stderr.decode(errors="replace")
    assert final_patch.returncode == 0, final_patch.stderr.decode(errors="replace")
    assert reset.returncode == 0, reset.stderr.decode(errors="replace")
    FINAL_PATHS.write_bytes(inventory.stdout)
    assert final_patch.stdout == CANDIDATE_PATCH.read_bytes(), (
        "the submitted source diff changed while verifier tests were running"
    )

    gates = _load_gates()
    failures = gates.submitted_path_failures(FINAL_PATHS)
    failures.extend(gates.check(REPO_ROOT, MANIFEST))
    assert not failures, "post-test integrity gate failed: " + "; ".join(failures)
