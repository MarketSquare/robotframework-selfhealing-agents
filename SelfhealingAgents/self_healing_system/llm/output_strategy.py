"""Output strategy layer for provider-aware output mode selection.

Selects the optimal pydantic-ai output mode (ToolOutput, NativeOutput,
PromptedOutput) based on provider capabilities and user configuration.
Provides prepare_tools hooks for dynamic tool schema adjustment.

New file. Part of ADR-001b Phase 2.
"""

from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel
from pydantic_ai.output import (
    NativeOutput,
    PromptedOutput,
    ToolOutput,
)
from pydantic_ai.tools import ToolDefinition

from SelfhealingAgents.utils.cfg import Cfg


# --- Provider capability constants ---

# Providers that support response_format: json_schema (NativeOutput)
_NATIVE_OUTPUT_PROVIDERS = {"openai", "azure"}

# Providers known to NOT support any tool-based output
# (empty by default; user sets OUTPUT_MODE=prompted for specific models)
_NO_TOOL_OUTPUT_PROVIDERS: set[str] = set()


# --- PromptedOutput template for locator healing ---

_LOCATOR_HEALING_PROMPTED_TEMPLATE = (
    "You must respond with ONLY a JSON object matching this schema. "
    "Do NOT include any explanation, markdown formatting, or code fences.\n\n"
    "JSON Schema:\n{schema}\n\n"
    "The 'suggestions' field must be a list of locator strings (CSS selectors, "
    "XPath expressions, or other locator formats). Each string should be a "
    "complete, valid locator that can be used directly in a test framework.\n\n"
    "The 'metadata' field is optional and should contain a list of objects "
    "with 'locator', 'reason', and 'confidence' keys describing each suggestion."
)


# --- Core output resolution ---

def resolve_structured_output_type(
    schema_class: type[BaseModel],
    cfg: Cfg,
    provider: str,
) -> type[BaseModel] | ToolOutput | NativeOutput | PromptedOutput:
    """Select the output type wrapper based on provider and config.

    For structured output (BaseModel schemas like LocatorHealingResponse),
    selects among NativeOutput, ToolOutput, and PromptedOutput based on
    provider capabilities and the OUTPUT_MODE configuration.

    Mode selection logic:
        - "native"   -> NativeOutput(schema_class)
        - "tool"     -> ToolOutput(schema_class) (equivalent to bare schema_class)
        - "prompted" -> PromptedOutput(schema_class, template=_LOCATOR_HEALING_PROMPTED_TEMPLATE)
        - "text"     -> PromptedOutput (text mode not applicable to structured; falls back)
        - "auto"     -> Provider-based selection (see _auto_resolve_mode)

    Args:
        schema_class: The Pydantic model class for structured output.
        cfg: Application configuration.
        provider: The provider name (e.g., 'openai', 'ollama', 'openrouter').

    Returns:
        A pydantic-ai output type wrapper appropriate for the provider.
    """
    mode = getattr(cfg, 'output_mode', 'auto')

    if mode == "native":
        return NativeOutput(schema_class)
    elif mode == "tool":
        return schema_class  # bare class = ToolOutput (default behavior)
    elif mode in ("prompted", "text"):
        return PromptedOutput(
            schema_class,
            template=_LOCATOR_HEALING_PROMPTED_TEMPLATE,
        )
    else:  # "auto"
        return _auto_resolve_structured(schema_class, provider)


def _auto_resolve_structured(
    schema_class: type[BaseModel],
    provider: str,
) -> type[BaseModel] | NativeOutput | PromptedOutput:
    """Auto-select the best output mode for a provider.

    Decision tree:
        1. OpenAI / Azure -> NativeOutput (response_format: json_schema)
        2. Provider in _NO_TOOL_OUTPUT_PROVIDERS -> PromptedOutput
        3. All others (openrouter, ollama-with-tools, vllm) -> ToolOutput (bare class)

    Args:
        schema_class: The Pydantic model class.
        provider: The provider name.

    Returns:
        The optimal output type for the provider.
    """
    if provider in _NATIVE_OUTPUT_PROVIDERS:
        return NativeOutput(schema_class)
    if provider in _NO_TOOL_OUTPUT_PROVIDERS:
        return PromptedOutput(
            schema_class,
            template=_LOCATOR_HEALING_PROMPTED_TEMPLATE,
        )
    return schema_class  # ToolOutput (default)


# --- prepare_tools hook ---

def make_prepare_tools_hook(
    provider: str,
    cfg: Cfg,
) -> Callable[
    [list[ToolDefinition], Any], list[ToolDefinition] | None
] | None:
    """Create a prepare_tools hook for provider-specific tool schema adjustment.

    The prepare_tools function receives ALL tool definitions at each agent
    step and can modify or filter them. This is applied AFTER any per-tool
    `prepare` function.

    Provider-specific adjustments:
        - ollama: Remove 'strict' and 'additionalProperties' from all tool schemas
        - vllm: Remove 'strict' from tool schemas; simplify nested types
        - openai/azure: No adjustment needed (native support)
        - openrouter: No adjustment needed (OpenRouterProvider handles it)

    Args:
        provider: The provider name.
        cfg: Application configuration.

    Returns:
        A prepare_tools callable, or None if no adjustment is needed.
    """
    if provider == "ollama":
        return _prepare_tools_ollama
    elif provider == "vllm":
        return _prepare_tools_vllm
    return None


async def _prepare_tools_ollama(
    ctx: Any,
    tools: list[ToolDefinition],
) -> list[ToolDefinition]:
    """Strip strict-mode artifacts from tool schemas for Ollama.

    Ollama tolerates but does not benefit from strict mode annotations.
    Some Ollama models may choke on additionalProperties: false in nested
    objects. This hook ensures clean schemas reach the Ollama API.

    Args:
        ctx: The run context (unused but required by signature).
        tools: List of tool definitions to modify.

    Returns:
        Modified tool definitions with strict artifacts removed.
    """
    for tool in tools:
        _strip_strict_from_schema(tool.parameters_json_schema)
    return tools


async def _prepare_tools_vllm(
    ctx: Any,
    tools: list[ToolDefinition],
) -> list[ToolDefinition]:
    """Strip strict-mode fields from tool schemas for vLLM.

    vLLM explicitly rejects requests containing 'strict: true' in tool
    definitions and does not support 'additionalProperties: false'. This
    hook acts as a safety net beyond the profile-level strict=False setting.

    Args:
        ctx: The run context (unused but required by signature).
        tools: List of tool definitions to modify.

    Returns:
        Modified tool definitions with strict fields removed.
    """
    for tool in tools:
        _strip_strict_from_schema(tool.parameters_json_schema)
    return tools


def _strip_strict_from_schema(schema: dict) -> None:
    """Recursively remove 'strict' and 'additionalProperties' from a JSON schema.

    Modifies the schema dict in place. Walks nested 'properties' and 'items'
    to ensure deeply nested schemas are also cleaned.

    Args:
        schema: JSON schema dict to clean.
    """
    schema.pop("strict", None)
    schema.pop("additionalProperties", None)
    for prop in schema.get("properties", {}).values():
        if isinstance(prop, dict):
            _strip_strict_from_schema(prop)
    items = schema.get("items")
    if isinstance(items, dict):
        _strip_strict_from_schema(items)
