"""LiteLLM provider builder with profile support.

Updated for ADR-001a to use OpenAIChatModel (not deprecated OpenAIModel),
fix double-path bug, and support strict_tool_definitions configuration.
"""
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.profiles.openai import OpenAIModelProfile
from SelfhealingAgents.utils.cfg import Cfg


def litellm_builder(model_name: str, cfg: Cfg) -> OpenAIChatModel:
    """Build an OpenAI-compatible model for LiteLLM.

    Args:
        model_name: The name of the model to use (e.g., 'gpt-4o-mini').
        cfg: The configuration object containing LiteLLM API credentials and settings.

    Returns:
        OpenAIChatModel configured for LiteLLM with appropriate profile settings.
    """
    # Use base_url directly - OpenAIProvider appends /chat/completions automatically
    # Previous implementation had a double-path bug by appending /v1/chat/completions
    base_url = cfg.base_url.rstrip("/") if cfg.base_url else None

    profile = OpenAIModelProfile(
        openai_supports_strict_tool_definition=cfg.strict_tool_definitions,
    )
    return OpenAIChatModel(
        model_name=model_name,
        provider=OpenAIProvider(
            api_key=cfg.litellm_api_key,
            base_url=base_url,
        ),
        profile=profile,
    )
