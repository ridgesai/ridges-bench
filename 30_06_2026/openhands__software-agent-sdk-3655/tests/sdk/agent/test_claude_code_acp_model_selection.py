from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from openhands.sdk.agent.acp_agent import ACPAgent
from openhands.sdk.settings.acp_providers import ACPProviderInfo, get_acp_provider


class FakeSecretRegistry:
    def __init__(self) -> None:
        self.secret_sources: dict[str, Any] = {}

    def get_secret_infos(self) -> list[dict[str, Any]]:
        return []

    def get_all_secrets_as_env_vars(
        self, exclude: set[str] | None = None
    ) -> dict[str, str]:
        return {}

    def get_secret_value(self, name: str) -> str | None:
        return None

    def mask_secrets_in_output(self, value: str) -> str:
        return value


class FakeWorkspace:
    def __init__(self) -> None:
        self.working_dir = "/workspace"


class FakeConversationState:
    def __init__(self) -> None:
        self.agent_state: dict[str, Any] = {}
        self.events: list[Any] = []
        self.execution_status: Any = "running"
        self.persistence_dir = None
        self.secret_registry = FakeSecretRegistry()
        self.workspace = FakeWorkspace()


class FakeConversation:
    def __init__(self, state: FakeConversationState) -> None:
        self.state = state


class ModelSelectionFailure(Exception):
    pass


class FakeAcpServer:
    def __init__(self, rejected_models: set[str] | None = None) -> None:
        self.current_model = "default"
        self.session_id = "session-1"
        self.rejected_models = set(rejected_models or set())
        self.stdout: asyncio.StreamReader | None = None
        self.ended = False

    def attach_stdout(self, stdout: asyncio.StreamReader) -> None:
        self.stdout = stdout

    def finish(self) -> None:
        if self.stdout is not None and not self.ended:
            self.stdout.feed_eof()
            self.ended = True

    def send(self, payload: dict[str, Any]) -> None:
        if self.stdout is None:
            raise RuntimeError("fake ACP stdout is not attached")
        line = json.dumps(payload, separators=(",", ":")).encode() + b"\n"
        self.stdout.feed_data(line)

    def handle_message(self, raw: bytes) -> None:
        request = json.loads(raw)
        request_id = request.get("id")
        if request_id is None:
            return

        method = str(request.get("method", ""))
        params = request.get("params") or {}
        if not isinstance(params, dict):
            params = {}
        normalized = method.replace("/", "_").replace("-", "_").lower()

        try:
            result = self.result_for(normalized, params)
        except ModelSelectionFailure as exc:
            self.send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32602, "message": str(exc)},
                }
            )
        else:
            self.send({"jsonrpc": "2.0", "id": request_id, "result": result})

    def result_for(self, normalized_method: str, params: dict[str, Any]) -> Any:
        if "initialize" in normalized_method:
            return {
                "protocolVersion": 1,
                "agentInfo": {"name": "claude-agent-acp", "version": "0.30.0"},
                "agentCapabilities": {"mcpCapabilities": {"http": False, "sse": False}},
                "authMethods": [],
            }

        if "session" in normalized_method and "new" in normalized_method:
            return {
                "sessionId": self.session_id,
                "models": {"currentModelId": self.current_model, "availableModels": []},
            }

        if "set_model" in normalized_method or "setmodel" in normalized_method:
            requested = (
                params.get("modelId")
                or params.get("model_id")
                or params.get("model")
                or params.get("value")
            )
            if requested in self.rejected_models:
                raise ModelSelectionFailure("model rejected by fake ACP server")
            self.current_model = str(requested)
            return None

        if "set_mode" in normalized_method or "setmode" in normalized_method:
            return None

        if "prompt" in normalized_method:
            return {"stopReason": "endTurn"}

        return None


class FakeAcpStdin(asyncio.StreamWriter):
    def __init__(self, server: FakeAcpServer) -> None:
        self.server = server
        self.buffer = b""
        self.closed = False

    def __del__(self) -> None:
        pass

    def write(self, data: bytes) -> None:
        self.buffer += bytes(data)
        self.consume_complete_messages()

    def consume_complete_messages(self) -> None:
        while b"\n" in self.buffer:
            raw, self.buffer = self.buffer.split(b"\n", 1)
            if raw.strip():
                self.server.handle_message(raw)

        candidate = self.buffer.strip()
        if not candidate.startswith(b"{"):
            return
        try:
            json.loads(candidate)
        except json.JSONDecodeError:
            return
        raw = self.buffer
        self.buffer = b""
        self.server.handle_message(raw)

    async def drain(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True
        self.server.finish()

    def is_closing(self) -> bool:
        return self.closed

    async def wait_closed(self) -> None:
        return None

    def can_write_eof(self) -> bool:
        return True

    def write_eof(self) -> None:
        self.close()


class FakeAcpProcess:
    def __init__(self, server: FakeAcpServer) -> None:
        self.stdout = asyncio.StreamReader()
        self.stderr = asyncio.StreamReader()
        self.stdin = FakeAcpStdin(server)
        self.returncode: int | None = None
        server.attach_stdout(self.stdout)

    def terminate(self) -> None:
        self.returncode = -15

    def kill(self) -> None:
        self.returncode = -9

    async def wait(self) -> int:
        return self.returncode or 0


async def fake_create_subprocess_exec_for(
    server: FakeAcpServer, *args: Any, **kwargs: Any
) -> FakeAcpProcess:
    return FakeAcpProcess(server)


def install_fake_acp_process(monkeypatch: pytest.MonkeyPatch, server: FakeAcpServer) -> None:
    async def fake_create_subprocess_exec(*args: Any, **kwargs: Any) -> FakeAcpProcess:
        return await fake_create_subprocess_exec_for(server, *args, **kwargs)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)


def test_claude_code_provider_uses_protocol_model_setting_and_keeps_meta_key() -> None:
    provider = get_acp_provider("claude-code")

    assert isinstance(provider, ACPProviderInfo)
    assert provider.supports_set_session_model is True
    assert provider.session_meta_key == "claudeCode"


def test_claude_code_init_applies_requested_model_to_acp_session(monkeypatch: pytest.MonkeyPatch) -> None:
    server = FakeAcpServer()
    install_fake_acp_process(monkeypatch, server)
    state = FakeConversationState()
    agent = ACPAgent(
        acp_command=["fake-claude-agent-acp"], acp_model="claude-opus-4-8"
    )

    agent.init_state(state, on_event=lambda event: state.events.append(event))

    assert agent.current_model_id == "claude-opus-4-8"
    assert server.current_model == "claude-opus-4-8"

    agent.step(FakeConversation(state), on_event=lambda event: state.events.append(event))


def test_claude_code_rejected_initial_model_surfaces_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    server = FakeAcpServer(rejected_models={"blocked-model"})
    install_fake_acp_process(monkeypatch, server)
    state = FakeConversationState()
    agent = ACPAgent(acp_command=["fake-claude-agent-acp"], acp_model="blocked-model")

    with pytest.raises(Exception):
        agent.init_state(state, on_event=lambda event: state.events.append(event))

    assert server.current_model == "default"
