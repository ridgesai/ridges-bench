from __future__ import annotations

import asyncio
import importlib
import inspect
from types import SimpleNamespace

from openhands.sdk.agent.acp_agent import ACPAgent


WORKING_DIR = '/workspace'
SERVER_DEFAULT_MODEL = 'server-default'


class FakeSecretRegistry:
    def __init__(self) -> None:
        self.secret_sources = {}

    def get_secret_infos(self):
        return []

    def get_all_secrets_as_env_vars(self, exclude=None):
        return {}

    def get_secret_value(self, name):
        return None

    def mask_secrets_in_output(self, text):
        return text


class FakeState:
    def __init__(self) -> None:
        self.agent_state = {}
        self.workspace = SimpleNamespace(working_dir=WORKING_DIR)
        self.persistence_dir = None
        self.secret_registry = FakeSecretRegistry()
        self.events = []
        self.execution_status = None


class InlineAsyncExecutor:
    @property
    def portal(self):
        raise AssertionError('portal is not needed by these synchronous tests')

    def run_async(self, awaitable_or_fn, *args, timeout=None, **kwargs):
        if inspect.iscoroutinefunction(awaitable_or_fn):
            awaitable = awaitable_or_fn(*args, **kwargs)
        elif inspect.iscoroutine(awaitable_or_fn):
            awaitable = awaitable_or_fn
        else:
            raise TypeError('expected a coroutine or coroutine function')
        return asyncio.run(awaitable)

    def close(self):
        return None


class FakeStdout:
    async def readline(self):
        return b''


class FakeProcess:
    def __init__(self) -> None:
        self.stdin = object()
        self.stdout = FakeStdout()
        self.stderr = FakeStdout()
        self.terminated = False
        self.killed = False

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True


def model_value_from_session_options(value):
    if isinstance(value, dict):
        direct = value.get('model')
        if isinstance(direct, str) and direct:
            return direct
        for nested in value.values():
            found = model_value_from_session_options(nested)
            if found is not None:
                return found
    return None


class InMemoryACPServer:
    def __init__(
        self,
        *,
        agent_name='custom-model-server',
        accepts_session_set_model=False,
    ) -> None:
        self.agent_name = agent_name
        self.accepts_session_set_model = accepts_session_set_model
        self.sessions = {}
        self.last_session_id = None
        self.next_session_number = 1
        self.closed = False

    async def initialize(self, protocol_version):
        return SimpleNamespace(
            agent_info=SimpleNamespace(name=self.agent_name, version='test'),
            agent_capabilities=None,
            auth_methods=[],
        )

    async def new_session(self, cwd, mcp_servers, **session_options):
        session_id = f'new-session-{self.next_session_number}'
        self.next_session_number += 1
        configured_model = model_value_from_session_options(session_options)
        self.sessions[session_id] = {
            'cwd': cwd,
            'model': configured_model or SERVER_DEFAULT_MODEL,
            'config': {},
        }
        self.last_session_id = session_id
        return SimpleNamespace(session_id=session_id)

    async def load_session(self, cwd, session_id, mcp_servers):
        self.sessions.setdefault(
            session_id,
            {'cwd': cwd, 'model': SERVER_DEFAULT_MODEL, 'config': {}},
        )
        self.last_session_id = session_id
        return SimpleNamespace()

    async def set_config_option(self, config_id, value, session_id):
        if value is None:
            raise AssertionError('a missing ACP model must not be applied')
        session = self.sessions[session_id]
        session['config'][config_id] = value
        if config_id == 'model':
            session['model'] = value

    async def set_session_model(self, model_id, session_id):
        if model_id is None:
            raise AssertionError('a missing ACP model must not be applied')
        if self.accepts_session_set_model:
            self.sessions[session_id]['model'] = model_id

    async def set_session_mode(self, mode_id, session_id):
        self.sessions[session_id]['mode'] = mode_id

    async def authenticate(self, method_id, **kwargs):
        return None

    async def close(self):
        self.closed = True

    async def prompt(self, prompt_blocks, session_id):
        return SimpleNamespace()

    def model_for(self, session_id):
        return self.sessions[session_id]['model']


def install_in_memory_acp(monkeypatch, server):
    acp_agent_module = importlib.import_module('openhands.sdk.agent.acp_agent')
    async_executor_module = importlib.import_module(
        'openhands.sdk.utils.async_executor'
    )

    async def fake_create_subprocess_exec(*args, **kwargs):
        return FakeProcess()

    monkeypatch.setattr(asyncio, 'create_subprocess_exec', fake_create_subprocess_exec)
    monkeypatch.setattr(
        acp_agent_module,
        'ClientSideConnection',
        lambda *args, **kwargs: server,
    )
    monkeypatch.setattr(async_executor_module, 'AsyncExecutor', InlineAsyncExecutor)


def start_agent(
    monkeypatch,
    server,
    *,
    acp_model=None,
    acp_resume_session_id=None,
    command=None,
):
    install_in_memory_acp(monkeypatch, server)
    agent = ACPAgent(
        acp_command=command or ['custom-acp'],
        acp_model=acp_model,
        acp_resume_session_id=acp_resume_session_id,
        acp_file_secrets=[],
    )
    state = FakeState()
    emitted_events = []
    agent.init_state(state, emitted_events.append)
    return agent, state, server


def supports_runtime_model_switch(agent):
    value = agent.supports_runtime_model_switch
    return value() if callable(value) else value


def test_custom_provider_new_session_uses_configured_model(monkeypatch):
    configured_model = 'custom-frontier-model'
    server = InMemoryACPServer()

    agent, state, server = start_agent(
        monkeypatch,
        server,
        acp_model=configured_model,
    )

    assert server.last_session_id is not None
    assert server.model_for(server.last_session_id) == configured_model


def test_custom_provider_without_configured_model_keeps_server_default(monkeypatch):
    server = InMemoryACPServer()

    agent, state, server = start_agent(monkeypatch, server)

    assert server.last_session_id is not None
    assert server.model_for(server.last_session_id) == SERVER_DEFAULT_MODEL


def test_custom_provider_resume_reapplies_stored_model(monkeypatch):
    stored_model = 'stored-custom-model'
    stored_session_id = 'stored-session'
    server = InMemoryACPServer()

    agent, state, server = start_agent(
        monkeypatch,
        server,
        acp_model=stored_model,
        acp_resume_session_id=stored_session_id,
    )

    assert server.model_for(stored_session_id) == stored_model


def test_custom_provider_runtime_switch_support_is_hidden_before_and_after_session(
    monkeypatch,
):
    unstarted_agent = ACPAgent(acp_command=['custom-acp'], acp_file_secrets=[])
    assert supports_runtime_model_switch(unstarted_agent) is False

    server = InMemoryACPServer()
    started_agent, state, server = start_agent(
        monkeypatch,
        server,
        acp_model='initial-custom-model',
    )

    assert supports_runtime_model_switch(started_agent) is False


def test_known_provider_runtime_switch_support_is_reported_after_session(monkeypatch):
    server = InMemoryACPServer(
        agent_name='codex-acp',
        accepts_session_set_model=True,
    )

    agent, state, server = start_agent(
        monkeypatch,
        server,
        command=['codex-acp'],
    )

    assert supports_runtime_model_switch(agent) is True


def test_step_without_user_message_finishes_cleanly(monkeypatch):
    server = InMemoryACPServer()
    agent, state, server = start_agent(monkeypatch, server)
    conversation = SimpleNamespace(state=state)

    agent.step(conversation, on_event=state.events.append)

    status = getattr(state.execution_status, 'value', state.execution_status)
    assert status == 'finished'
