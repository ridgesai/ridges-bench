import asyncio
import inspect
import sys
from collections.abc import Mapping

import pytest

from openhands.sdk.agent.acp_agent import ACPAgent

MISSING = object()


class AwaitableResult:
    def __init__(self, value):
        self.value = value

    def __await__(self):
        async def done():
            return self.value

        return done().__await__()

    def __getattr__(self, name):
        return getattr(self.value, name)


class FlexibleValue:
    def __init__(self, **values):
        for name, value in values.items():
            setattr(self, name, value)

    def __getattr__(self, name):
        if name in {'http', 'sse', 'stdio'}:
            return True
        value = FlexibleValue()
        setattr(self, name, value)
        return value

    def __getitem__(self, name):
        return getattr(self, name)

    def __contains__(self, name):
        return True

    def __iter__(self):
        return iter(())

    def __bool__(self):
        return True

    def __call__(self, *args, **kwargs):
        return self

    def __await__(self):
        async def done():
            return self

        return done().__await__()

    def get(self, name, default=None):
        return getattr(self, name, default)


class MinimalSecretRegistry:
    secret_sources = ()

    def get_secret_infos(self):
        return []

    def get_all_secrets_as_env_vars(self, exclude=None):
        return {}

    def get_secret_value(self, name):
        return None

    def mask_secrets_in_output(self, value):
        return value


class ProviderMethod:
    def __init__(self, provider, name):
        self.provider = provider
        self.name = name

    def __call__(self, *args, **kwargs):
        return self.provider.respond(self.name, args, kwargs)

    def __getattr__(self, name):
        return ProviderMethod(self.provider, f'{self.name}.{name}')


class CapturingProvider:
    def __init__(self, recorder):
        self.recorder = recorder

    def __getattr__(self, name):
        return ProviderMethod(self, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    def respond(self, name, args, kwargs):
        self.recorder.record(args)
        self.recorder.record(kwargs)
        response = FlexibleValue(
            id='session-id',
            session_id='session-id',
            sessionId='session-id',
            capabilities=FlexibleValue(),
            agents=[FlexibleValue(id='test-agent', name='test-agent')],
        )
        return AwaitableResult(response)

    def close(self):
        return AwaitableResult(None)

    def aclose(self):
        return AwaitableResult(None)


class ProviderHandle:
    def __init__(self, provider):
        self.provider = provider

    def __iter__(self):
        yield self.provider
        yield self.provider

    def __getattr__(self, name):
        return getattr(self.provider, name)


class FakeAsyncContext:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, traceback):
        return None


class ACPRecorder:
    def __init__(self):
        self.seen_servers = []

    def record(self, value):
        servers = find_mcp_servers(value)
        if servers is not None:
            self.seen_servers.append(servers)

    def latest_servers(self):
        if not self.seen_servers:
            pytest.fail('ACPAgent did not send any MCP server configuration to the ACP provider')
        return self.seen_servers[-1]


def find_mcp_servers(value, seen=None):
    if seen is None:
        seen = set()
    if value is None or isinstance(value, (str, bytes, FlexibleValue, ProviderMethod, CapturingProvider)):
        return None
    value_id = id(value)
    if value_id in seen:
        return None
    seen.add(value_id)

    if isinstance(value, Mapping):
        for key in ('mcp_servers', 'mcpServers'):
            if key in value:
                return value[key]
        for nested in value.values():
            result = find_mcp_servers(nested, seen)
            if result is not None:
                return result
        return None

    if isinstance(value, (list, tuple, set, frozenset)):
        for nested in value:
            result = find_mcp_servers(nested, seen)
            if result is not None:
                return result
        return None

    for method_name in ('model_dump', 'dict'):
        method = getattr(value, method_name, None)
        if callable(method):
            try:
                dumped = method()
            except TypeError:
                continue
            result = find_mcp_servers(dumped, seen)
            if result is not None:
                return result

    try:
        attributes = vars(value)
    except TypeError:
        attributes = None
    if attributes:
        result = find_mcp_servers(attributes, seen)
        if result is not None:
            return result

    for field in ('mcp_servers', 'mcpServers'):
        try:
            candidate = getattr(value, field)
        except Exception:
            candidate = None
        if candidate is not None:
            return candidate
    return None


def install_fake_acp_provider(monkeypatch, provider):
    module = sys.modules[ACPAgent.__module__]

    def provider_factory(*args, **kwargs):
        return provider

    def context_factory(*args, **kwargs):
        return FakeAsyncContext(ProviderHandle(provider))

    def process_value(*args, **kwargs):
        return FlexibleValue(stdin=provider, stdout=provider, stderr=provider, returncode=0)

    def async_process_factory(*args, **kwargs):
        return AwaitableResult(process_value())

    async def filter_noop(source, dest):
        dest.feed_eof()

    for name in ('Client', 'ACPClient', 'AgentClient', 'ClientSideConnection', 'Connection', 'SessionClient'):
        if hasattr(module, name):
            monkeypatch.setattr(module, name, provider_factory)

    for name in ('stdio_client', 'sse_client', 'streamablehttp_client', 'connect_stdio', 'connect_sse', 'connect_http', 'connect'):
        if hasattr(module, name):
            monkeypatch.setattr(module, name, context_factory)

    for name in ('create_subprocess_exec', 'open_process'):
        if hasattr(module, name):
            monkeypatch.setattr(module, name, async_process_factory)

    if hasattr(module, 'subprocess'):
        monkeypatch.setattr(module.subprocess, 'Popen', process_value, raising=False)
    if hasattr(module, 'asyncio'):
        monkeypatch.setattr(module.asyncio, 'create_subprocess_exec', async_process_factory, raising=False)
    if hasattr(module, 'anyio'):
        monkeypatch.setattr(module.anyio, 'open_process', async_process_factory, raising=False)
    if hasattr(module, '_filter_jsonrpc_lines'):
        monkeypatch.setattr(module, '_filter_jsonrpc_lines', filter_noop)


def constructor_attempts(mcp_config, provider):
    broad = {
        'mcp_config': mcp_config,
        'name': 'test-agent',
        'agent_id': 'test-agent',
        'id': 'test-agent',
        'client': provider,
        'acp_client': provider,
        'provider': provider,
        'connection': provider,
        'command': ['test-acp-agent'],
        'args': [],
        'env': {},
        'headers': {},
        'url': 'http://acp.example.test',
        'endpoint': 'http://acp.example.test',
        'cwd': None,
        'working_dir': None,
        'tools': [],
        'llm': None,
        'runtime': None,
        'config': {'command': ['test-acp-agent']},
        'server_config': {'command': ['test-acp-agent']},
        'acp_config': {'command': ['test-acp-agent']},
    }

    attempts = []
    fields = getattr(ACPAgent, 'model_fields', None) or getattr(ACPAgent, '__fields__', None)
    if isinstance(fields, Mapping):
        attempts.append({key: value for key, value in broad.items() if key in fields})

    try:
        signature = inspect.signature(ACPAgent)
    except (TypeError, ValueError):
        signature = None

    if signature is not None:
        kwargs = {}
        accepts_keywords = False
        for name, parameter in signature.parameters.items():
            if name == 'self' or parameter.kind is inspect.Parameter.VAR_POSITIONAL:
                continue
            if parameter.kind is inspect.Parameter.VAR_KEYWORD:
                accepts_keywords = True
                continue
            value = value_for_parameter(name, parameter, mcp_config, provider)
            if value is not MISSING:
                kwargs[name] = value
        if accepts_keywords:
            for key, value in broad.items():
                kwargs.setdefault(key, value)
        attempts.append(kwargs)
        if 'command' in kwargs:
            alternate = dict(kwargs)
            alternate['command'] = 'test-acp-agent'
            attempts.append(alternate)

    attempts.append(broad)
    attempts.append({'mcp_config': mcp_config, 'client': provider})
    attempts.append({'mcp_config': mcp_config, 'acp_client': provider})

    for attempt in attempts:
        yield filter_constructor_kwargs(attempt, signature)


def filter_constructor_kwargs(kwargs, signature):
    if signature is None:
        return kwargs
    if any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values()):
        return kwargs
    return {key: value for key, value in kwargs.items() if key in signature.parameters}


def value_for_parameter(name, parameter, mcp_config, provider):
    lower = name.lower()
    if name == 'mcp_config' or ('mcp' in lower and 'config' in lower):
        return mcp_config
    if lower in {'client', 'acp_client', 'provider', 'connection'} or lower.endswith('_client'):
        return provider
    if 'config' in lower:
        return {'command': ['test-acp-agent']}
    if parameter.default is not inspect.Parameter.empty:
        return MISSING
    if 'name' in lower or lower in {'id', 'agent_id'} or lower.endswith('id'):
        return 'test-agent'
    if 'command' in lower or 'cmd' in lower:
        return ['test-acp-agent']
    if 'args' in lower or 'argv' in lower or 'tools' in lower:
        return []
    if 'env' in lower or 'headers' in lower:
        return {}
    if 'url' in lower or 'endpoint' in lower:
        return 'http://acp.example.test'
    if 'server' in lower:
        return {'command': ['test-acp-agent']}
    if 'cwd' in lower or 'dir' in lower:
        return None
    return None


def make_agent(monkeypatch, mcp_config):
    recorder = ACPRecorder()
    provider = CapturingProvider(recorder)
    install_fake_acp_provider(monkeypatch, provider)
    last_error = None
    for kwargs in constructor_attempts(mcp_config, provider):
        try:
            return ACPAgent(**kwargs), recorder
        except Exception as exc:
            last_error = exc
    pytest.fail(f'Could not construct ACPAgent through its public constructor: {last_error}')


async def resolve(value):
    if inspect.isawaitable(value):
        return await value
    return value


async def call_public_init_state(agent):
    signature = inspect.signature(agent.init_state)
    args = []
    kwargs = {}
    state = FlexibleValue(
        agent_state={},
        persistence_dir=None,
        secret_registry=MinimalSecretRegistry(),
        workspace=FlexibleValue(working_dir='/tmp'),
    )
    on_event = lambda event: None
    for name, parameter in signature.parameters.items():
        if name == 'self' or parameter.default is not inspect.Parameter.empty:
            continue
        if name == 'state':
            value = state
        elif name == 'on_event' or 'event' in name.lower():
            value = on_event
        else:
            value = None
        if parameter.kind is inspect.Parameter.KEYWORD_ONLY:
            kwargs[name] = value
        elif parameter.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            args.append(value)
    return await resolve(agent.init_state(*args, **kwargs))


async def call_public_close(agent):
    return await resolve(agent.close())


def init_and_capture_server(monkeypatch, server_spec, server_name='remote'):
    spec = {'url': 'https://mcp.example.test/mcp', 'transport': 'http'}
    spec.update(server_spec)
    mcp_config = {'mcpServers': {server_name: spec}}
    agent, recorder = make_agent(monkeypatch, mcp_config)
    try:
        asyncio.run(call_public_init_state(agent))
        return server_named(recorder.latest_servers(), server_name)
    finally:
        asyncio.run(call_public_close(agent))


def public_value(value, *names):
    if isinstance(value, Mapping):
        for name in names:
            if name in value:
                return value[name]
    for name in names:
        try:
            return getattr(value, name)
        except Exception:
            pass
    for method_name in ('model_dump', 'dict'):
        method = getattr(value, method_name, None)
        if callable(method):
            try:
                dumped = method()
            except TypeError:
                continue
            if isinstance(dumped, Mapping):
                for name in names:
                    if name in dumped:
                        return dumped[name]
    raise AssertionError(f'Missing one of fields {names!r} on {value!r}')


def server_named(servers, server_name):
    if isinstance(servers, Mapping):
        if server_name in servers:
            return servers[server_name]
        candidates = list(servers.values())
    elif isinstance(servers, (list, tuple, set, frozenset)):
        candidates = list(servers)
    else:
        candidates = [servers]

    for server in candidates:
        try:
            if public_value(server, 'name') == server_name:
                return server
        except AssertionError:
            continue
    if len(candidates) == 1:
        return candidates[0]
    pytest.fail(f'ACP provider did not receive MCP server {server_name!r}')


def header_pairs(server):
    raw_headers = public_value(server, 'headers')
    assert raw_headers is not None
    pairs = []
    for header in raw_headers:
        pairs.append((public_value(header, 'name'), public_value(header, 'value')))
    return pairs


def values_for_header(pairs, header_name):
    return [value for name, value in pairs if str(name).lower() == header_name.lower()]


def test_remote_mcp_string_auth_is_forwarded_as_authorization_header(monkeypatch):
    server = init_and_capture_server(monkeypatch, {'auth': 'remote-token'})

    pairs = header_pairs(server)

    assert ('Authorization', 'Bearer remote-token') in pairs


def test_explicit_authorization_header_is_not_replaced_by_auth(monkeypatch):
    server = init_and_capture_server(
        monkeypatch,
        {
            'auth': 'remote-token',
            'headers': {'Authorization': 'Explicit credential'},
        },
    )

    pairs = header_pairs(server)

    assert values_for_header(pairs, 'Authorization') == ['Explicit credential']
    assert 'Bearer remote-token' not in values_for_header(pairs, 'Authorization')


def test_non_authorization_remote_mcp_headers_are_forwarded(monkeypatch):
    server = init_and_capture_server(
        monkeypatch,
        {
            'auth': 'remote-token',
            'headers': {'X-Workspace': 'scout', 'X-Trace-Id': 'trace-123'},
        },
    )

    pairs = header_pairs(server)

    assert ('X-Workspace', 'scout') in pairs
    assert ('X-Trace-Id', 'trace-123') in pairs
