"""OpenAI provider builder with profile support.

Updated for ADR-001a to use OpenAIChatModel (not deprecated OpenAIModel)
and support strict_tool_definitions configuration.
"""
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.profiles.openai import OpenAIModelProfile
from SelfhealingAgents.utils.cfg import Cfg


def openai_builder(model_name: str, cfg: Cfg) -> OpenAIChatModel:
    """Build an OpenAI model with profile configuration.

    Args:
        model_name: The OpenAI model identifier (e.g., 'gpt-4o-mini').
        cfg: Application configuration.

    Returns:
        OpenAIChatModel with appropriate profile settings.
    """
    profile = OpenAIModelProfile(
        openai_supports_strict_tool_definition=cfg.strict_tool_definitions,
    )
    return OpenAIChatModel(
        model_name=model_name,
        provider=OpenAIProvider(
            api_key=cfg.openai_api_key,
            base_url=cfg.base_url,
        ),
        profile=profile,
    )
