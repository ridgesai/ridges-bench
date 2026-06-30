from collections.abc import Mapping

import pytest
from pydantic import SecretStr

from openhands.sdk.agent.acp_agent import ACPAgent
from openhands.sdk.context.agent_context import AgentContext
from openhands.sdk.conversation.request import StartConversationRequest
from openhands.sdk.secret import StaticSecret
from openhands.sdk.settings.model import ACPAgentSettings, ConversationSettings
from openhands.sdk.workspace import LocalWorkspace


LLM_API_KEY = "llm-api-key-must-not-be-promoted"
LLM_BASE_URL = "https://llm-base-url.example.invalid/v1"
SUPPORTED_PROVIDER_API_KEY = "provider-secret-from-agent-context"


def settings_with_llm_credentials(*, api_key=None, base_url=None):
    settings = ACPAgentSettings()
    llm_updates = {}
    if api_key is not None:
        llm_updates["api_key"] = api_key
    if base_url is not None:
        llm_updates["base_url"] = base_url

    llm = settings.llm.model_copy(update=llm_updates)
    return settings.model_copy(update={"llm": llm})


def request_secrets(request):
    secrets = getattr(request, "secrets", None)
    if secrets is None:
        return {}
    assert isinstance(secrets, Mapping)
    return secrets


def contains_plain_value(value, expected):
    if value == expected:
        return True

    get_secret_value = getattr(value, "get_secret_value", None)
    if get_secret_value is not None and get_secret_value() == expected:
        return True

    if hasattr(value, "value") and contains_plain_value(value.value, expected):
        return True

    if isinstance(value, Mapping):
        return any(
            contains_plain_value(item_key, expected)
            or contains_plain_value(item_value, expected)
            for item_key, item_value in value.items()
        )

    if isinstance(value, (list, tuple, set)):
        return any(contains_plain_value(item, expected) for item in value)

    model_dump = getattr(value, "model_dump", None)
    if model_dump is not None:
        return contains_plain_value(model_dump(), expected)

    return False


def request_from_settings(settings):
    return ConversationSettings(agent_settings=settings).create_request(
        StartConversationRequest,
        workspace=LocalWorkspace(working_dir="/tmp"),
    )


def settings_and_request_with_agent_context_secret(secret_name, secret_value):
    settings = ACPAgentSettings(
        agent_context=AgentContext(
            current_datetime=None,
            secrets={
                secret_name: StaticSecret(value=SecretStr(secret_value)),
            },
        )
    )
    request = request_from_settings(settings)
    assert secret_name in request_secrets(request)
    return settings, request


@pytest.mark.parametrize(
    "llm_updates",
    [
        {"api_key": LLM_API_KEY},
        {"base_url": LLM_BASE_URL},
    ],
)
def test_create_agent_warns_for_deprecated_llm_credentials(llm_updates):
    settings = settings_with_llm_credentials(**llm_updates)

    with pytest.warns(DeprecationWarning):
        agent = settings.create_agent()

    assert isinstance(agent, ACPAgent)


def test_create_agent_does_not_promote_llm_api_key_to_request_secrets():
    settings = settings_with_llm_credentials(api_key=LLM_API_KEY)

    with pytest.warns(DeprecationWarning):
        agent = settings.create_agent()

    assert isinstance(agent, ACPAgent)

    with pytest.warns(DeprecationWarning):
        request = request_from_settings(settings)

    secrets = request_secrets(request)
    assert settings.api_key_env_var not in secrets
    assert not contains_plain_value(secrets, LLM_API_KEY)


def test_create_agent_does_not_promote_llm_base_url_to_request_secrets():
    settings = settings_with_llm_credentials(base_url=LLM_BASE_URL)

    with pytest.warns(DeprecationWarning):
        agent = settings.create_agent()

    assert isinstance(agent, ACPAgent)

    with pytest.warns(DeprecationWarning):
        request = request_from_settings(settings)

    secrets = request_secrets(request)
    assert settings.base_url_env_var not in secrets
    assert not contains_plain_value(secrets, LLM_BASE_URL)


def test_agent_context_provider_secret_is_carried_into_conversation_request():
    env_name = ACPAgentSettings().api_key_env_var
    settings, request = settings_and_request_with_agent_context_secret(
        env_name,
        SUPPORTED_PROVIDER_API_KEY,
    )

    secrets = request_secrets(request)
    assert env_name == settings.api_key_env_var
    assert env_name in secrets
    assert contains_plain_value(secrets[env_name], SUPPORTED_PROVIDER_API_KEY)


def test_resolve_provider_env_still_returns_legacy_llm_mapping_with_warning():
    settings = settings_with_llm_credentials(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
    )

    with pytest.warns(DeprecationWarning):
        provider_env = settings.resolve_provider_env()

    assert provider_env == {
        settings.api_key_env_var: LLM_API_KEY,
        settings.base_url_env_var: LLM_BASE_URL,
    }
