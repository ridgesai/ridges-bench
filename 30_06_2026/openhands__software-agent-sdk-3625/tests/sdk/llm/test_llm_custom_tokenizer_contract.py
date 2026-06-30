import os

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

import builtins
import importlib
import types

import pytest

from openhands.sdk.llm.llm import LLM


class FakeLiteLLMEncoding:
    ids = [0]


class FakeLiteLLMTokenizer:
    def encode(self, text):
        return FakeLiteLLMEncoding()


class FakeContent:
    def __init__(self):
        self.cache_prompt = False


class FakeMessage:
    def __init__(self, text="hello", role="user"):
        self.role = role
        self.text = text
        self.content = [FakeContent()]

    def to_chat_dict(self, **kwargs):
        return {"role": self.role, "content": self.text}


class FakeTool:
    def __init__(self, payload):
        self.payload = payload

    def to_openai_tool(self, add_security_risk_prediction=False):
        return self.payload


@pytest.fixture
def lite_hf_tokenizer(monkeypatch):
    import litellm.utils

    def from_pretrained(cls, *args, **kwargs):
        return FakeLiteLLMTokenizer()

    monkeypatch.setattr(
        litellm.utils.Tokenizer,
        "from_pretrained",
        classmethod(from_pretrained),
    )


def install_transformers_import(monkeypatch, module_or_exception):
    real_import_module = importlib.import_module
    real_import = builtins.__import__

    def is_transformers_name(name):
        return name == "transformers" or name.startswith("transformers.")

    def resolve_transformers():
        if isinstance(module_or_exception, BaseException):
            raise module_or_exception
        return module_or_exception

    def fake_import_module(name, package=None):
        if is_transformers_name(name):
            return resolve_transformers()
        return real_import_module(name, package)

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level == 0 and is_transformers_name(name):
            return resolve_transformers()
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)
    monkeypatch.setattr(builtins, "__import__", fake_import)


def transformers_module_returning(tokenizer_or_factory):
    class FakeAutoTokenizer:
        @classmethod
        def from_pretrained(cls, identifier):
            if callable(tokenizer_or_factory):
                return tokenizer_or_factory(identifier)
            return tokenizer_or_factory

    return types.SimpleNamespace(AutoTokenizer=FakeAutoTokenizer)


def build_llm(**overrides):
    options = {
        "model": "gpt-4o",
        "api_key": "test-key",
        "caching_prompt": False,
        "disable_vision": True,
        "num_retries": 0,
    }
    options.update(overrides)
    return LLM(**options)


def test_custom_tokenizer_requires_transformers_at_initialization(
    monkeypatch, lite_hf_tokenizer
):
    install_transformers_import(monkeypatch, ModuleNotFoundError("transformers"))

    with pytest.raises(ModuleNotFoundError):
        build_llm(custom_tokenizer="example/chat-template-tokenizer")


def test_custom_tokenizer_requires_auto_tokenizer(monkeypatch, lite_hf_tokenizer):
    install_transformers_import(
        monkeypatch,
        types.SimpleNamespace(AutoTokenizer=None),
    )

    with pytest.raises(RuntimeError):
        build_llm(custom_tokenizer="example/chat-template-tokenizer")


def test_custom_tokenizer_load_failure_is_initialization_error(
    monkeypatch, lite_hf_tokenizer
):
    def fail_to_load(identifier):
        raise OSError("cannot load tokenizer")

    install_transformers_import(
        monkeypatch,
        transformers_module_returning(fail_to_load),
    )

    with pytest.raises(RuntimeError):
        build_llm(custom_tokenizer="example/missing-tokenizer")


def test_custom_tokenizer_requires_apply_chat_template(monkeypatch, lite_hf_tokenizer):
    install_transformers_import(
        monkeypatch,
        transformers_module_returning(object()),
    )

    with pytest.raises(ValueError):
        build_llm(custom_tokenizer="example/no-chat-template-method")


def test_custom_tokenizer_requires_defined_chat_template(monkeypatch, lite_hf_tokenizer):
    class TokenizerWithoutTemplate:
        chat_template = None

        def apply_chat_template(self, messages, **kwargs):
            return []

    install_transformers_import(
        monkeypatch,
        transformers_module_returning(TokenizerWithoutTemplate()),
    )

    with pytest.raises(ValueError):
        build_llm(custom_tokenizer="example/no-chat-template")


def test_get_token_count_with_custom_tokenizer_uses_chat_template_and_tools(
    monkeypatch, lite_hf_tokenizer
):
    tool_payload = {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "finish the task",
            "parameters": {"type": "object", "properties": {}},
        },
    }

    class CountingChatTemplateTokenizer:
        chat_template = "{{ messages }}"

        def apply_chat_template(self, messages, **kwargs):
            if (
                messages == [{"role": "user", "content": "hello from user"}]
                and kwargs.get("tools") == [tool_payload]
                and kwargs.get("tokenize") is True
                and kwargs.get("add_generation_prompt") is True
            ):
                return list(range(321))
            return list(range(9))

    install_transformers_import(
        monkeypatch,
        transformers_module_returning(CountingChatTemplateTokenizer()),
    )
    llm = build_llm(custom_tokenizer="example/chat-template-tokenizer")

    count = llm.get_token_count(
        [FakeMessage("hello from user")],
        tools=[FakeTool(tool_payload)],
    )

    assert count == 321


def test_get_token_count_with_custom_tokenizer_propagates_template_errors(
    monkeypatch, lite_hf_tokenizer
):
    class ChatTemplateFailure(RuntimeError):
        pass

    class FailingChatTemplateTokenizer:
        chat_template = "{{ messages }}"

        def apply_chat_template(self, messages, **kwargs):
            raise ChatTemplateFailure()

    install_transformers_import(
        monkeypatch,
        transformers_module_returning(FailingChatTemplateTokenizer()),
    )
    llm = build_llm(custom_tokenizer="example/broken-chat-template-tokenizer")

    with pytest.raises(ChatTemplateFailure):
        llm.get_token_count([FakeMessage("hello")])


def test_get_token_count_without_custom_tokenizer_keeps_litellm_path_available():
    llm = build_llm(custom_tokenizer=None)

    count = llm.get_token_count([FakeMessage("hello from user")])

    assert isinstance(count, int)
    assert count > 0
