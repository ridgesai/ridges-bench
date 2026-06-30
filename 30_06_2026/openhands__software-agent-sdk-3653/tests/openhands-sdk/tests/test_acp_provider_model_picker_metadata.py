from openhands.sdk.settings.acp_providers import (
    ACPModelOption,
    ACPProviderInfo,
    get_acp_provider,
)


def model_ids(provider: ACPProviderInfo) -> list[str]:
    return [model.id for model in provider.available_models]


def test_codex_provider_omits_known_bad_gpt_5_3_codex_variants() -> None:
    provider = get_acp_provider("codex")
    ids = set(model_ids(provider))

    assert ids.isdisjoint(
        {
            "gpt-5.3-codex/low",
            "gpt-5.3-codex/medium",
            "gpt-5.3-codex/high",
            "gpt-5.3-codex/xhigh",
        }
    )


def test_codex_provider_omits_unsupported_gpt_5_2_variants() -> None:
    provider = get_acp_provider("codex")
    ids = set(model_ids(provider))

    assert ids.isdisjoint(
        {
            "gpt-5.2/low",
            "gpt-5.2/medium",
            "gpt-5.2/high",
            "gpt-5.2/xhigh",
        }
    )


def test_codex_provider_advertises_only_supported_codex_model_choices() -> None:
    provider = get_acp_provider("codex")

    assert isinstance(provider, ACPProviderInfo)
    assert all(isinstance(model, ACPModelOption) for model in provider.available_models)
    assert model_ids(provider) == [
        "gpt-5.5/low",
        "gpt-5.5/medium",
        "gpt-5.5/high",
        "gpt-5.5/xhigh",
        "gpt-5.4-mini/low",
        "gpt-5.4-mini/medium",
        "gpt-5.4-mini/high",
        "gpt-5.4-mini/xhigh",
    ]


def test_claude_code_provider_advertises_curated_current_generation_models() -> None:
    provider = get_acp_provider("claude-code")

    assert isinstance(provider, ACPProviderInfo)
    assert all(isinstance(model, ACPModelOption) for model in provider.available_models)
    assert model_ids(provider) == [
        "claude-fable-5",
        "claude-opus-4-8",
        "opus[1m]",
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
        "opusplan",
    ]


def test_claude_code_provider_default_model_is_current_opus() -> None:
    provider = get_acp_provider("claude-code")

    assert provider.default_model == "claude-opus-4-8"
