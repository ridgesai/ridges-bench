import os
import shlex
import shutil
import subprocess
import time

import pytest

from openhands.tools.terminal.terminal.subprocess_terminal import SubprocessTerminal
from openhands.tools.terminal.terminal.tmux_terminal import TmuxTerminal


EXPECTED_GREP_LINE = "1:def encode(payload):"


def _require_program(name: str) -> None:
    if shutil.which(name) is None:
        pytest.skip(f"{name} is required for this terminal integration test")


def _git_env(tmp_path):
    env = os.environ.copy()
    env.pop("GIT_PAGER", None)
    env.pop("PAGER", None)
    env.update(
        {
            "GIT_AUTHOR_NAME": "Terminal Pager Test",
            "GIT_AUTHOR_EMAIL": "terminal-pager-test@example.com",
            "GIT_COMMITTER_NAME": "Terminal Pager Test",
            "GIT_COMMITTER_EMAIL": "terminal-pager-test@example.com",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "HOME": str(tmp_path / "home"),
            "XDG_CONFIG_HOME": str(tmp_path / "xdg-config"),
        }
    )
    return env


def _run_git(repo, env, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        env=env,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _make_repo_with_large_patch(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (tmp_path / "home").mkdir()
    (tmp_path / "xdg-config").mkdir()

    env = _git_env(tmp_path)
    _run_git(repo, env, "init")
    _run_git(repo, env, "config", "user.name", "Terminal Pager Test")
    _run_git(repo, env, "config", "user.email", "terminal-pager-test@example.com")
    _run_git(repo, env, "config", "commit.gpgsign", "false")
    _run_git(repo, env, "config", "core.pager", "less")

    lines = [
        "def encode(payload):",
        "    return f\"encoded:{payload}\"",
        "",
    ]
    lines.extend(f"FILLER_{index:03d} = {index}" for index in range(300))
    (repo / "codec.py").write_text("\n".join(lines) + "\n", encoding="utf-8")

    _run_git(repo, env, "add", "codec.py")
    _run_git(repo, env, "commit", "-m", "add large codec fixture")
    return repo


def _screen_text(screen) -> str:
    return str(screen).replace("\r", "")


def _wait_until_idle(terminal, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not terminal.is_running():
            return True
        time.sleep(0.05)
    return False


def _wait_for_screen_text(terminal, expected: str, timeout: float = 3.0) -> str:
    deadline = time.monotonic() + timeout
    screen = ""
    while time.monotonic() < deadline:
        screen = _screen_text(terminal.read_screen())
        if expected in screen:
            return screen
        time.sleep(0.05)
    return screen


@pytest.mark.parametrize(
    "terminal_cls",
    [
        pytest.param(SubprocessTerminal, id="subprocess"),
        pytest.param(TmuxTerminal, id="tmux"),
    ],
)
def test_pager_producing_git_command_does_not_capture_follow_up_command(
    terminal_cls, tmp_path, monkeypatch
):
    _require_program("git")
    _require_program("less")
    if terminal_cls is TmuxTerminal:
        _require_program("tmux")

    monkeypatch.delenv("GIT_PAGER", raising=False)
    monkeypatch.delenv("PAGER", raising=False)
    monkeypatch.delenv("LESS", raising=False)

    repo = _make_repo_with_large_patch(tmp_path)
    terminal = terminal_cls(str(repo))

    try:
        terminal.initialize()
        terminal.send_keys(f"cd {shlex.quote(str(repo))}")
        terminal.send_keys("git log -p -- codec.py")
        if _wait_until_idle(terminal):
            terminal.clear_screen()
        terminal.send_keys('grep --color=never -n "^def encode" codec.py')
        screen = _wait_for_screen_text(terminal, EXPECTED_GREP_LINE)
    finally:
        terminal.close()

    assert EXPECTED_GREP_LINE in screen
