"""OpenRouter provider builder using native OpenRouterProvider.

New file. Part of ADR-001a Phase 1.
"""
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from SelfhealingAgents.utils.cfg import Cfg


def openrouter_builder(model_name: str, cfg: Cfg) -> OpenAIChatModel:
    """Build an OpenAI-compatible model using OpenRouterProvider.

    OpenRouterProvider handles finish_reason quirks, metadata nullability,
    and model-specific behaviors internally. Most reliable path for non-OpenAI models.

    Args:
        model_name: The model identifier (e.g., 'mistralai/devstral-2512').
        cfg: Application configuration.

    Returns:
        OpenAIChatModel configured for OpenRouter.
    """
    return OpenAIChatModel(
        model_name=model_name,
        provider=OpenRouterProvider(api_key=cfg.openai_api_key),
    )
