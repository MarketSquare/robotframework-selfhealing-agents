"""LLM provider builders for different backends.

This package provides builder functions for creating OpenAIChatModel instances
configured for various LLM providers (OpenAI, Azure, OpenRouter, Ollama, LiteLLM).
"""
from SelfhealingAgents.self_healing_system.llm.providers.openai_builder import openai_builder
from SelfhealingAgents.self_healing_system.llm.providers.azure_builder import azure_builder
from SelfhealingAgents.self_healing_system.llm.providers.openrouter_builder import openrouter_builder
from SelfhealingAgents.self_healing_system.llm.providers.ollama_builder import ollama_builder
from SelfhealingAgents.self_healing_system.llm.providers.litellm_builder import litellm_builder

__all__ = [
    "openai_builder",
    "azure_builder",
    "openrouter_builder",
    "ollama_builder",
    "litellm_builder",
]
