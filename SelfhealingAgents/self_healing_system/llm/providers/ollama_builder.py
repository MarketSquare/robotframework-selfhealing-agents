"""Ollama provider builder with strict=False default.

New file. Part of ADR-001a Phase 1.
"""
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.profiles.openai import OpenAIModelProfile
from SelfhealingAgents.utils.cfg import Cfg


def ollama_builder(model_name: str, cfg: Cfg) -> OpenAIChatModel:
    """Build an OpenAI-compatible model for Ollama.

    Ollama models do not support strict tool definitions. This builder
    hardcodes strict=False and uses a dummy API key ('ollama') as required
    by the OpenAI SDK.

    Args:
        model_name: The Ollama model identifier (e.g., 'qwen3:latest').
        cfg: Application configuration.

    Returns:
        OpenAIChatModel configured for Ollama with strict=False.
    """
    return OpenAIChatModel(
        model_name=model_name,
        provider=OpenAIProvider(
            api_key="ollama",
            base_url=cfg.base_url or "http://localhost:11434/v1",
        ),
        profile=OpenAIModelProfile(
            openai_supports_strict_tool_definition=False,
        ),
    )
