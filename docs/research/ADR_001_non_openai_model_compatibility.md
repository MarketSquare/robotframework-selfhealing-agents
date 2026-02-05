# ADR-001: Non-OpenAI Model Compatibility Architecture

**Status:** Proposed (v2 -- consolidated 2026-02-04)
**Date:** 2026-02-04
**Decision Makers:** Project maintainers
**Branch:** feature/improve_nonopenai_model_function_calls

---

## Table of Contents

1. [Context and Problem Statement](#1-context-and-problem-statement)
2. [Decision Drivers](#2-decision-drivers)
3. [DDD Bounded Contexts](#3-ddd-bounded-contexts)
4. [ADR-001a: Provider Abstraction Layer](#4-adr-001a-provider-abstraction-layer)
5. [ADR-001b: Output Strategy and Fallback Mechanism](#5-adr-001b-output-strategy-and-fallback-mechanism)
6. [ADR-001c: Configuration and Capability Detection](#6-adr-001c-configuration-and-capability-detection)
7. [ADR-001d: OrchestratorAgent Refactoring](#7-adr-001d-orchestrator-agent-refactoring)
8. [ADR-001e: Schema Improvements](#8-adr-001e-schema-improvements)
9. [Implementation Plan](#9-implementation-plan)
10. [Testing Strategy](#10-testing-strategy)
11. [Migration Guide](#11-migration-guide)
12. [Risk Analysis](#12-risk-analysis)
13. [ADR-001f: Advanced Tool Features](#13-adr-001f-advanced-tool-features)
14. [ADR-001g: Extensible Healing Type Architecture](#14-adr-001g-extensible-healing-type-architecture)
15. [ADR-001h: Orchestrator Hybrid Routing for Multi-Healing](#15-adr-001h-orchestrator-hybrid-routing-for-multi-healing)
16. [ADR-001i: Context Enrichment and DDD Expansion](#16-adr-001i-context-enrichment-and-ddd-expansion)

[Glossary](#glossary)

---

## Glossary

| Term | Definition |
|------|-----------|
| **ToolOutput** | pydantic-ai output mode where the model calls a hidden tool to produce structured output. Passing a bare `schema_class` to pydantic-ai as `output_type=MyModel` is equivalent to `output_type=ToolOutput(MyModel)`. Throughout this document, "ToolOutput" refers to both forms. |
| **NativeOutput** | pydantic-ai output mode using `response_format: json_schema`. The model produces JSON directly without tool calls. Most reliable for OpenAI/Azure. |
| **PromptedOutput** | pydantic-ai output mode where the JSON schema is injected into the prompt text. Universal compatibility but lower reliability. |
| **Programmatic Hand-Off** | pydantic-ai multi-agent pattern where application code (not the LLM) decides which agent to call next. Used when routing is deterministic. Defined in section 7.1. |
| **Agent Delegation** | pydantic-ai multi-agent pattern using `output_type=[function]` where the LLM decides to call a tool that delegates to another agent. The current (pre-refactoring) orchestrator pattern. |
| **`output_type=[function]` pattern** | The mechanism where a function is passed as a list element to `output_type`, causing pydantic-ai to register it as a tool the model must call. This is the mechanism underlying the Agent Delegation design pattern. |
| **LocatorHealingResponse** | The Pydantic model representing structured healing output, containing `suggestions: list[str]` and `metadata: list[dict]`. |
| **NoHealingNeededResponse** | The Pydantic model returned when the error is not a locator error and no healing is needed. |

---

## 1. Context and Problem Statement

### 1.1 Current State

The `robotframework-selfhealing-agents` project uses pydantic-ai v1.54.0 for LLM-powered
locator healing. All models are routed through `OpenAIModel` + `OpenAIProvider` without
any `ModelProfile` configuration, inheriting OpenAI-specific defaults (strict tool
definitions, required tool choice).

### 1.2 Problem

When non-OpenAI models are used through OpenAI-compatible endpoints (OpenRouter, Ollama,
vLLM, LiteLLM), several compatibility failures occur:

| Failure Mode | Affected Models | Root Cause |
|---|---|---|
| Timeout with `strict: true` | kimi-k2.5 | Model chokes on `additionalProperties: false` |
| Text instead of tool call | minimax-m2.1 (typed schema), devstral (Ollama) | Weak tool-calling support |
| XML tool call format | mimo-v2-flash | Non-standard tool response format |
| `output_type=[function]` pattern fails | ALL Ollama models | Ollama rejects tool result messages |
| No tool support at all | gemma3:12b (Ollama) | Model lacks tool-calling capability |
| `strict: true` rejected | vLLM providers | Provider doesn't support strict mode |
| `tool_choice: required` rejected | vLLM, Bedrock Llama | Provider doesn't support required |

### 1.3 Scope of Empirical Testing

8 models tested across 2 providers:

**OpenRouter:** devstral-2512 (7/7), qwen3-coder-next (7/7), kimi-k2.5 (6/7),
minimax-m2.1 (6/7), mimo-v2-flash (6/7)

**Ollama:** qwen3 (8/9), devstral (7/9), gemma3:12b (1/9, only PromptedOutput)

### 1.4 Current Architecture

```
.env -> Cfg -> ModelFactory -> entry_point builder -> OpenAIModel (no profile)
                                                        |
                                          Agent(output_type=...)
```

Three agent types:
- **OrchestratorAgent**: `output_type=[self._get_healed_locators]` (Agent Delegation via `output_type=[function]` pattern)
- **Locator Generation Agent**: `output_type=LocatorHealingResponse` (ToolOutput structured output)
- **Locator Selection Agent**: `output_type=str` (plain text)

---

## 2. Decision Drivers

1. **Reliability across providers**: Solution must work with OpenAI, OpenRouter, Ollama,
   vLLM, and future providers without per-model code changes
2. **Backward compatibility**: Existing OpenAI + OpenRouter devstral users must not break
3. **Minimal code change**: Prefer configuration over code changes where possible
4. **Automatic fallback**: Gracefully degrade when model capabilities are limited
5. **Testability**: Each component must be independently testable with mocked providers
6. **DDD principles**: Clean bounded contexts with clear interfaces

---

## 3. DDD Bounded Contexts

### 3.1 Context Map

```
+--------------------------------------------------------------------------------------+
|                              Self-Healing System                                      |
|                                                                                      |
|  +--------------+  +--------------+  +------------------+  +---------------------+  |
|  |   Provider    |  |   Output     |  |  Agent            |  |  Error              |  |
|  |   Context     |->|   Strategy   |<-|  Orchestration    |<-|  Classification     |  |
|  |              |  |   Context    |  |  Context          |  |  Context            |  |
|  +------+-------+  +------+-------+  +--------+----------+  +----------+----------+  |
|         |                 |                   |                        |              |
|  +------+-------+  +------+-------+  +-------+----------+  +---------+-----------+  |
|  | Configuration |  |   Schema     |  |  Context          |  |  Reporting          |  |
|  | Context      |  |   Context    |  |  Enrichment       |  |  Context            |  |
|  +--------------+  +--------------+  +-------------------+  +---------------------+  |
+--------------------------------------------------------------------------------------+
```

### 3.2 Bounded Context Definitions

| Context | Responsibility | Key Files |
|---------|---------------|-----------|
| **Provider** | Model creation, profile configuration, provider-specific adapters | `providers/`, `model_factory.py`, `client_model.py` |
| **Output Strategy** | Output mode selection, fallback logic, PromptedOutput wrapping | New: `output_strategy.py` |
| **Agent Orchestration** | Agent creation, tool registration, execution flow, healing type dispatch | `orchestrator_agent.py`, `base_locator_agent.py`, future: `base_healing_agent.py` |
| **Configuration** | Environment loading, capability mapping, validation | `cfg.py` |
| **Schema** | Response models, JSON schema generation, type constraints, `HealingPayload`, `HealingResponse` | `locator_healing.py`, `healing_payload.py`, `prompt_payload.py` |
| **Error Classification** | Classify keyword failures into healing types (locator, timing, assertion, mandatory_field) | New: `error_classifier.py` |
| **Context Enrichment** | Strategy-based context gathering, screenshot capture, user story retrieval, token budget management | `robot_ctx_retriever.py`, `strategies/`, `screenshot_capturer.py`, `user_story_retriever.py`, `token_budget.py` |
| **Reporting** | Multi-healing-type report generation and data collection | `report_data.py`, new: `healing_report_data.py` |

### 3.3 Context Relationships

```
Error Classification --(healing_type)--> Context Enrichment --(HealingPayload)--> Agent Orchestration
                                              |
                                              +-- LocatorContextStrategy --> BaseDomUtils
                                              +-- TimingContextStrategy --> BaseDomUtils + BuiltIn
                                              +-- AssertionContextStrategy --> UserStoryRetriever + ScreenshotCapturer
                                              +-- MandatoryFieldContextStrategy --> BaseDomUtils + ScreenshotCapturer

Agent Orchestration --(healing result)--> Reporting
```

The **Error Classification** context is an upstream dependency that determines which
context strategy runs. Its design is covered in ADR-001g (section 14); this section
assumes its output is a string healing type identifier.

> **Note:** The original 5 bounded contexts (Provider, Output Strategy, Agent Orchestration,
> Configuration, Schema) were defined in ADR-001 v1. The 3 new contexts (Error
> Classification, Context Enrichment, Reporting) were introduced in sections 14-16 and
> are consolidated here for a complete picture.

---

## 4. ADR-001a: Provider Abstraction Layer

### 4.1 Decision

Replace the current flat builder pattern with a **provider strategy** that encapsulates
model creation, profile configuration, and provider-specific behavior.

### 4.2 Current State

```python
# openai_builder.py -- no profile, deprecated class
def openai_builder(model_name: str, cfg: Cfg) -> OpenAIModel:
    return OpenAIModel(
        model_name=model_name,
        provider=OpenAIProvider(api_key=cfg.openai_api_key, base_url=cfg.base_url),
    )
```

Problems:
- No `ModelProfile` -> inherits `strict: true`, `tool_choice: required`
- Uses deprecated `OpenAIModel` -> deprecation warnings
- No OpenRouter-specific provider -> misses finish_reason handling
- No Ollama-specific provider -> no fallback behavior
- LiteLLM builder has double-path bug

### 4.3 Proposed Design

#### 4.3.1 Updated Builder Interface

Each builder returns `OpenAIChatModel` (not deprecated `OpenAIModel`) and accepts a
profile parameter. The builder is responsible for selecting the correct provider class
and profile defaults for its target platform.

#### 4.3.2 Builder Implementations

**openai_builder.py** (for actual OpenAI API):
```python
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.profiles.openai import OpenAIModelProfile
from SelfhealingAgents.utils.cfg import Cfg

def openai_builder(model_name: str, cfg: Cfg) -> OpenAIChatModel:
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
```

**openrouter_builder.py** (NEW -- uses native OpenRouterProvider):
```python
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from SelfhealingAgents.utils.cfg import Cfg

def openrouter_builder(model_name: str, cfg: Cfg) -> OpenAIChatModel:
    return OpenAIChatModel(
        model_name=model_name,
        provider=OpenRouterProvider(api_key=cfg.openai_api_key),
    )
```

Rationale: `OpenRouterProvider` is the most reliable path -- all 5 tested models passed
all 7 tests. It handles `finish_reason` quirks, metadata nullability, and model-specific
behaviors internally.

**ollama_builder.py** (NEW -- strict=false by default):
```python
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.profiles.openai import OpenAIModelProfile
from SelfhealingAgents.utils.cfg import Cfg

def ollama_builder(model_name: str, cfg: Cfg) -> OpenAIChatModel:
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
```

**azure_builder.py** (updated to use `OpenAIChatModel`):
```python
from openai import AsyncAzureOpenAI
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.azure import AzureProvider
from SelfhealingAgents.utils.cfg import Cfg

def azure_builder(model_name: str, cfg: Cfg) -> OpenAIChatModel:
    return OpenAIChatModel(
        model_name=model_name,
        provider=AzureProvider(
            openai_client=AsyncAzureOpenAI(
                api_key=cfg.azure_api_key,
                api_version=cfg.azure_api_version,
                azure_endpoint=cfg.azure_endpoint,
            )
        ),
    )
```

**litellm_builder.py** (fix double-path bug + add profile):
```python
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.profiles.openai import OpenAIModelProfile
from SelfhealingAgents.utils.cfg import Cfg

def litellm_builder(model_name: str, cfg: Cfg) -> OpenAIChatModel:
    profile = OpenAIModelProfile(
        openai_supports_strict_tool_definition=cfg.strict_tool_definitions,
    )
    return OpenAIChatModel(
        model_name=model_name,
        provider=OpenAIProvider(
            api_key=cfg.litellm_api_key,
            base_url=cfg.base_url,  # No more appending /v1/chat/completions
        ),
        profile=profile,
    )
```

#### 4.3.3 model_factory.py Updates

```python
from pydantic_ai.models.openai import OpenAIChatModel  # Updated import

class ModelFactory:
    _builders: Dict[str, Callable[[str, Cfg], OpenAIChatModel]]

    def create_model(self, provider: str, model_name: str, cfg: Cfg) -> OpenAIChatModel:
        ...
```

#### 4.3.4 client_model.py Updates

```python
from pydantic_ai.models.openai import OpenAIChatModel  # Updated import

def get_client_model(*, provider: str, model: str, cfg: Cfg) -> OpenAIChatModel | None:
    ...
```

#### 4.3.5 pyproject.toml Entry Points

```toml
[project.entry-points."SelfhealingAgents.llm_model_providers"]
openai = "SelfhealingAgents.self_healing_system.llm.providers.openai_builder:openai_builder"
openrouter = "SelfhealingAgents.self_healing_system.llm.providers.openrouter_builder:openrouter_builder"
ollama = "SelfhealingAgents.self_healing_system.llm.providers.ollama_builder:ollama_builder"
azure = "SelfhealingAgents.self_healing_system.llm.providers.azure_builder:azure_builder"
litellm = "SelfhealingAgents.self_healing_system.llm.providers.litellm_builder:litellm_builder"
```

### 4.4 File Changes Summary

| File | Change Type | Description |
|------|------------|-------------|
| `providers/openai_builder.py` | MODIFY | Add profile, use `OpenAIChatModel` |
| `providers/openrouter_builder.py` | CREATE | New builder using `OpenRouterProvider` |
| `providers/ollama_builder.py` | CREATE | New builder with `strict=False` default |
| `providers/azure_builder.py` | MODIFY | Use `OpenAIChatModel` |
| `providers/litellm_builder.py` | MODIFY | Fix double-path, add profile, use `OpenAIChatModel` |
| `model_factory.py` | MODIFY | Update type hint to `OpenAIChatModel` |
| `client_model.py` | MODIFY | Update type hint to `OpenAIChatModel` |
| `pyproject.toml` | MODIFY | Add `openrouter` and `ollama` entry points |

---

## 5. ADR-001b: Output Strategy and Fallback Mechanism (Revised)

### 5.1 Decision

Introduce a **tri-modal output strategy layer** that selects the optimal pydantic-ai
output mode from all three available modes (ToolOutput, NativeOutput,
PromptedOutput) based on provider capabilities and configuration, with automatic
fallback and provider-aware `prepare_tools` hooks.

### 5.2 Revision Context

The original ADR-001b treated output as a binary choice: ToolOutput or PromptedOutput.
New pydantic-ai documentation reveals **three distinct output modes** plus several
supporting features that enable a more nuanced and reliable strategy:

| Feature | Original ADR Understanding | Revised Understanding |
|---|---|---|
| Output modes | 2 (tool, prompted) | **3** (ToolOutput, NativeOutput, PromptedOutput) |
| NativeOutput | Not considered | Uses `response_format: json_schema`. Most reliable for OpenAI. |
| PromptedOutput template | Not considered | Customizable via `template` parameter for domain-specific prompts |
| TextOutput(function) | Not considered | Plain-text-to-function marker; evaluated and rejected for orchestrator (see section 7) |
| Union output types | Not considered | `Model1 | Model2` pattern for multi-response agents |
| prepare_tools | Not considered | Agent-wide hook to modify ALL tool definitions per step |
| end_strategy | Not considered | `'early'` vs `'exhaustive'` control over tool execution |
| StructuredDict | Not considered | Runtime-generated schemas from JSON schema dicts |

### 5.3 Problem Analysis (Updated)

Four output modes exist in pydantic-ai, each with different compatibility and reliability
characteristics:

| Mode | Syntax | Mechanism | Reliability | Compatibility |
|------|--------|-----------|-------------|---------------|
| **ToolOutput** (default) | `output_type=Model` or `ToolOutput(Model)` | Hidden tool definition; model calls tool | High for tool-capable models | OpenAI, OpenRouter, Ollama (some) |
| **NativeOutput** | `NativeOutput(Model)` | `response_format: json_schema` | **Highest** for OpenAI/Azure | OpenAI, Azure. NOT OpenRouter/Ollama. |
| **PromptedOutput** | `PromptedOutput(Model)` | Schema injected into prompt text | Medium | **Universal** -- works everywhere |
| **Function Tool** | `output_type=[function]` | Model calls function tool, result returned to model | High but fragile | OpenAI, OpenRouter (most). **Fails ALL Ollama** |

Additional output mechanisms relevant to this project:

| Mechanism | Syntax | Use Case |
|---|---|---|
| **TextOutput(fn)** | `TextOutput(parse_function)` | Model returns text, function parses it. Alternative to `output_type=[function]` pattern. |
| **Union types** | `output_type=ModelA | ModelB` | Model chooses which type to produce. Agent validates against all. |

Current failure matrix for the `output_type=[function]` pattern (OrchestratorAgent's Agent Delegation pattern):

| Provider/Model | Failure Mode |
|---|---|
| Ollama qwen3 | `400: invalid message content type: <nil>` |
| Ollama devstral | Never makes tool call, exceeds retries |
| Ollama gemma3 | Model doesn't support tools |
| OpenRouter mimo-v2-flash | XML tool call format, JSON parse error |

### 5.4 Provider-to-Output-Mode Mapping

Based on empirical testing and pydantic-ai documentation, each provider maps to an
optimal output mode for structured output (locator healing):

| Provider | Optimal Mode | Rationale | Fallback |
|---|---|---|---|
| `openai` | **NativeOutput** | `response_format: json_schema` is OpenAI's most reliable structured output. Avoids tool_choice issues entirely. | ToolOutput |
| `azure` | **NativeOutput** | Azure OpenAI supports the same `response_format` as OpenAI. | ToolOutput |
| `openrouter` | **ToolOutput** | OpenRouterProvider handles tool quirks internally. NativeOutput not reliably supported across routed models. | PromptedOutput |
| `ollama` (with tools) | **ToolOutput** with `strict=False` | qwen3 supports tools. ToolOutput works when strict mode is disabled. | PromptedOutput |
| `ollama` (without tools) | **PromptedOutput** | gemma3 and similar models lack tool support entirely. | N/A (only option) |
| `vllm` | **ToolOutput** with `strict=False` | vLLM rejects `strict: true` and `tool_choice: required`. | PromptedOutput |
| `litellm` | **ToolOutput** | Proxy-dependent. Same as upstream provider behavior. | PromptedOutput |

> **Ollama auto-detection limitation:** Auto mode cannot distinguish tool-capable from
> non-tool-capable Ollama models at runtime. The provider name alone does not indicate
> whether a specific model supports tools (e.g., qwen3 supports tools but gemma3:12b does
> not). Users must manually set `OUTPUT_MODE=prompted` for Ollama models without tool
> support. There is no reliable runtime probe for this capability.

### 5.5 Proposed Design: Tri-Modal Output Strategy

#### 5.5.1 Configuration

Expand `output_mode` from the original 3 values (`tool`, `prompted`, `auto`) to 5,
adding the two new modes:

```python
# In Cfg
output_mode: str = Field(
    "auto", env="OUTPUT_MODE",
    description=(
        "Output mode for structured responses: "
        "'tool' (ToolOutput -- tool-based, requires model tool support), "
        "'native' (NativeOutput -- response_format json_schema, OpenAI/Azure only), "
        "'prompted' (PromptedOutput -- text-based, universal compatibility), "
        "'text' (TextOutput -- plain text parsed by function, reserved for future use), "
        "'auto' (select best mode based on provider). "
        "Default 'auto' uses NativeOutput for OpenAI/Azure, ToolOutput for "
        "OpenRouter/Ollama-with-tools, and PromptedOutput for Ollama-without-tools. "
        "Note: orchestrator uses Programmatic Hand-Off (no LLM), so output_mode "
        "only affects locator agents."
    ),
)
```

#### 5.5.2 Output Strategy Module

Create `SelfhealingAgents/self_healing_system/llm/output_strategy.py`:

```python
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
    TextOutput,
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
    mode = cfg.output_mode

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


# --- Orchestrator-specific output resolution ---
# NOTE (ADR-001d revised): The orchestrator now uses Programmatic Hand-Off
# (no LLM calls), so it does not need output mode resolution. Functions
# resolve_orchestrator_output_mode() and supports_function_output() that
# appeared in v1 have been removed.


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
    tools: list[ToolDefinition],
    ctx: Any,
) -> list[ToolDefinition]:
    """Strip strict-mode artifacts from tool schemas for Ollama.

    Ollama tolerates but does not benefit from strict mode annotations.
    Some Ollama models may choke on additionalProperties: false in nested
    objects. This hook ensures clean schemas reach the Ollama API.

    Args:
        tools: List of tool definitions to modify.
        ctx: The run context (unused but required by signature).

    Returns:
        Modified tool definitions with strict artifacts removed.
    """
    for tool in tools:
        _strip_strict_from_schema(tool.parameters_json_schema)
    return tools


async def _prepare_tools_vllm(
    tools: list[ToolDefinition],
    ctx: Any,
) -> list[ToolDefinition]:
    """Strip strict-mode fields from tool schemas for vLLM.

    vLLM explicitly rejects requests containing 'strict: true' in tool
    definitions and does not support 'additionalProperties: false'. This
    hook acts as a safety net beyond the profile-level strict=False setting.

    Args:
        tools: List of tool definitions to modify.
        ctx: The run context (unused but required by signature).

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
```

#### 5.5.3 PromptedOutput Template Design for Locator Healing

The default `PromptedOutput` injects a generic "respond with JSON matching this schema"
instruction. For locator healing, a domain-specific template significantly improves
output quality by telling the model what locators look like.

**Template anatomy:**

```
PromptedOutput(
    LocatorHealingResponse,
    template=_LOCATOR_HEALING_PROMPTED_TEMPLATE,
)
```

The `{schema}` placeholder is replaced by pydantic-ai with the JSON schema of
`LocatorHealingResponse`. The surrounding text provides domain context:

```
You must respond with ONLY a JSON object matching this schema.
Do NOT include any explanation, markdown formatting, or code fences.

JSON Schema:
{schema}

The 'suggestions' field must be a list of locator strings (CSS selectors,
XPath expressions, or other locator formats). Each string should be a
complete, valid locator that can be used directly in a test framework.

The 'metadata' field is optional and should contain a list of objects
with 'locator', 'reason', and 'confidence' keys describing each suggestion.
```

**Why this matters:** In testing with gemma3:12b (no tool support), the default
`PromptedOutput` template produced valid output, but a domain-specific template would
reduce ambiguity in the `suggestions` field format (e.g., preventing the model from
returning `{"locator": "#btn", "type": "css"}` objects instead of plain `"#btn"` strings).

**Template customization via environment variable (future):** If users need to
customize the template (e.g., for non-English prompts or alternative locator formats),
a `PROMPTED_OUTPUT_TEMPLATE` environment variable could be added. This is deferred to
avoid premature configuration complexity.

#### 5.5.4 TextOutput for Orchestrator -- Evaluated and Rejected

TextOutput for orchestration was evaluated and rejected in favor of Programmatic
Hand-Off (see section 7). The `TextOutput(parse_function)` pattern remains available
as a pydantic-ai feature for future use if LLM-based orchestration becomes necessary
(e.g., for multi-healing-type classification). See section 7.5.3 for details.

#### 5.5.5 Union Output Types

pydantic-ai supports `output_type=ModelA | ModelB`, where the model chooses which type
to produce. This is relevant for the locator agent, which could return:

```python
output_type = LocatorHealingResponse | NoHealingNeededResponse
```

However, this pattern is **not recommended for this project** because:

1. The orchestrator already decides whether healing is needed (via
   `is_failed_locator_error()`). Adding union output to the locator agent would
   duplicate this decision at a lower level.
2. Union output increases schema complexity for the model, which hurts weaker models.
3. The `NoHealingNeededResponse` path is never reached by the locator agent -- it is
   only constructed by the orchestrator.

**Decision:** Do not use union output types. Keep the current single-type pattern for
each agent.

#### 5.5.6 end_strategy

pydantic-ai's `end_strategy` parameter controls when the agent stops after producing
output:

- `end_strategy='early'` (default): Stop after the first valid output tool call.
- `end_strategy='exhaustive'`: Execute ALL function tools before stopping.

For this project:

- **Locator agents** should use `'early'` (default). Once `LocatorHealingResponse` is
  produced, there is no benefit to running additional tools.

**Decision:** Use default `end_strategy='early'` for all agents. No code change needed.

#### 5.5.7 StructuredDict for Dynamic Schemas

`StructuredDict(json_schema_dict)` allows creating output types from raw JSON schema
dicts at runtime. This could be useful if:

- Users wanted to define custom response schemas via configuration
- The schema needed to vary based on locator type (CSS vs XPath vs accessibility)

**Decision:** Do not use `StructuredDict` now. The `LocatorHealingResponse` schema is
stable and well-defined. `StructuredDict` is noted as a future option if schema
customization becomes a requirement.

#### 5.5.8 prepare_tools Hook Design

The `prepare_tools` parameter on `Agent` receives ALL tool definitions at each step
and can modify or filter them. This is applied AFTER any per-tool `prepare` function.

**Use cases for this project:**

1. **Strip strict-mode artifacts for Ollama/vLLM:** Even with `ModelProfile(strict=False)`,
   some schema transformations may leave `additionalProperties: false` in nested objects.
   `prepare_tools` acts as a safety net.

2. **Dynamic tool filtering:** If the orchestrator has multiple tools in the future,
   `prepare_tools` could hide irrelevant tools based on the error type.

3. **Logging/observability:** `prepare_tools` can log the exact tool schemas sent to
   each provider for debugging compatibility issues.

**Integration with agent creation:**

```python
from SelfhealingAgents.self_healing_system.llm.output_strategy import make_prepare_tools_hook

# In base_locator_agent.py __init__:
prepare_tools_hook = make_prepare_tools_hook(
    provider=cfg.locator_agent_provider,
    cfg=cfg,
)

self.generation_agent = Agent[PromptPayload, LocatorHealingResponse](
    model=get_client_model(...),
    output_type=output_type,
    prepare_tools=prepare_tools_hook,  # NEW: provider-aware tool adjustment
    ...
)
```

The hook is `None` for providers that do not need adjustment (OpenAI, Azure, OpenRouter),
so the agent uses default behavior. For Ollama and vLLM, the hook strips strict-mode
fields as a defense-in-depth measure.

#### 5.5.9 Output Validators with Streaming Awareness

pydantic-ai's `@agent.output_validator` receives a `ctx` with a `partial_output`
attribute when used with streaming. The current project uses `agent.run()` (not
`agent.run_stream()`), so this is not immediately relevant.

However, the existing `validate_output` in `base_locator_agent.py` should be
**streaming-safe** in case the project adds streaming later:

```python
@self.generation_agent.output_validator
async def validate_output(
    ctx: RunContext[PromptPayload],
    output: LocatorHealingResponse,
) -> LocatorHealingResponse:
    # Future-proof: skip validation during partial streaming
    if hasattr(ctx, 'partial_output') and ctx.partial_output:
        return output
    # ... existing validation logic ...
```

**Decision:** Add the `partial_output` guard as a forward-compatible change. No
functional impact on current non-streaming usage.

### 5.6 Integration Points (Updated)

#### 5.6.1 base_locator_agent.py -- uses `resolve_structured_output_type()` and `make_prepare_tools_hook()`

```python
from SelfhealingAgents.self_healing_system.llm.output_strategy import (
    resolve_structured_output_type,
    make_prepare_tools_hook,
)

# In __init__, when creating generation_agent:
output_type = resolve_structured_output_type(
    LocatorHealingResponse,
    cfg,
    cfg.locator_agent_provider,
)
prepare_tools_hook = make_prepare_tools_hook(
    provider=cfg.locator_agent_provider,
    cfg=cfg,
)
self.generation_agent = Agent[PromptPayload, LocatorHealingResponse](
    model=get_client_model(...),
    output_type=output_type,
    prepare_tools=prepare_tools_hook,
    ...
)
```

**Behavior by provider:**

| Provider | `output_type` | `prepare_tools` | Effect |
|---|---|---|---|
| `openai` | `NativeOutput(LocatorHealingResponse)` | `None` | Uses `response_format: json_schema`. No tool definitions sent. |
| `azure` | `NativeOutput(LocatorHealingResponse)` | `None` | Same as OpenAI. |
| `openrouter` | `LocatorHealingResponse` (bare = ToolOutput) | `None` | ToolOutput via OpenRouterProvider. |
| `ollama` (auto) | `LocatorHealingResponse` (bare = ToolOutput) | `_prepare_tools_ollama` | ToolOutput with strict artifacts stripped. |
| `ollama` (prompted) | `PromptedOutput(LocatorHealingResponse, template=...)` | `_prepare_tools_ollama` | Schema in prompt text. prepare_tools is a no-op since no tools sent. |
| `vllm` | `LocatorHealingResponse` (bare = ToolOutput) | `_prepare_tools_vllm` | ToolOutput with strict fields stripped. |

#### 5.6.2 orchestrator_agent.py -- Programmatic Hand-Off (no output strategy needed)

With the ADR-001d (revised) decision to use Programmatic Hand-Off, the orchestrator no
longer makes LLM calls and therefore does not need `resolve_structured_output_type()` or
any output mode resolution. See section 7.4 for the full design.

### 5.7 Alternatives Considered (Updated)

| Alternative | Pros | Cons | Decision |
|---|---|---|---|
| Always use PromptedOutput | Simplest, universal | Lower quality output, no tool validation | Rejected -- too much quality loss for OpenAI/OpenRouter |
| Always use NativeOutput | Most reliable for OpenAI | Not supported by OpenRouter/Ollama | Rejected -- not universal |
| Binary tool/prompted only | Simpler than tri-modal | Misses NativeOutput reliability gain for OpenAI | Rejected -- leaving performance on the table |
| Runtime capability probing | Automatic detection | Extra API call per model, latency | Rejected -- too complex, fragile |
| Per-model configuration file | Fine-grained control | Maintenance burden, user complexity | Rejected -- config explosion |
| **Tri-modal with provider defaults** | Optimal per provider, extensible, backward-compatible | Slightly more code than binary | **Selected** |

---

## 6. ADR-001c: Configuration and Capability Detection

### 6.1 Decision

Extend `Cfg` with provider-specific settings for tool definitions, output mode, and
Ollama-specific parameters. Use provider name as the primary capability discriminator.

### 6.2 New Configuration Fields

```python
class Cfg(BaseSettings):
    # ... existing fields ...

    # --- New fields for non-OpenAI compatibility ---

    strict_tool_definitions: bool = Field(
        True, env="STRICT_TOOL_DEFINITIONS",
        description=(
            "Enable strict tool definitions (adds 'strict: true' and "
            "'additionalProperties: false' to tool schemas). "
            "Set to False for non-OpenAI models that reject or choke on strict mode. "
            "Default True preserves current behavior for OpenAI users."
        ),
    )

    output_mode: str = Field(
        "auto", env="OUTPUT_MODE",
        description=(
            "Output mode for structured responses: "
            "'tool' (ToolOutput -- tool-based, requires model tool support), "
            "'native' (NativeOutput -- response_format json_schema, OpenAI/Azure only), "
            "'prompted' (PromptedOutput -- text-based, universal compatibility), "
            "'text' (TextOutput -- plain text parsed by function, reserved for future use), "
            "'auto' (select best mode based on provider). "
            "Default 'auto' uses NativeOutput for OpenAI/Azure, ToolOutput for "
            "OpenRouter/Ollama-with-tools, and PromptedOutput for Ollama-without-tools. "
            "Note: orchestrator uses Programmatic Hand-Off (no LLM), so output_mode "
            "only affects locator agents."
        ),
    )
```

> **`strict_tool_definitions` provider support:** This field is honored by the `openai`
> and `litellm` builders, which pass it to `OpenAIModelProfile`. The `ollama` builder
> always sets `strict=False` regardless of this field. The `azure` and `openrouter`
> builders do not yet configure this field (Azure inherits provider defaults; OpenRouter
> delegates to `OpenRouterProvider` which handles strict behavior per-model).

### 6.3 Provider Capability Matrix (Built-In Defaults, Revised)

The output strategy module encodes empirically verified defaults. The "Auto Structured"
column shows which output mode `resolve_structured_output_type()` selects in `auto`
mode. The "Orchestrator" column reflects the ADR-001d revision: all providers now use
Programmatic Hand-Off (no LLM call in orchestrator).

| Provider | `strict` Default | Auto Structured | Orchestrator | NativeOutput | ToolOutput | Notes |
|---|---|---|---|---|---|---|
| `openai` | From config (`True`) | **NativeOutput** | Programmatic Hand-Off | Yes | Yes | Full OpenAI API |
| `azure` | `True` (Azure OpenAI) | **NativeOutput** | Programmatic Hand-Off | Yes | Yes | Same as OpenAI |
| `openrouter` | N/A (handled by provider) | **ToolOutput** | Programmatic Hand-Off | No (model-dependent) | Yes | OpenRouterProvider handles quirks |
| `ollama` | `False` (hardcoded) | **ToolOutput** | Programmatic Hand-Off | No | Model-dependent | Tool result message fails for locator agents; orchestrator unaffected |
| `vllm` | `False` | **ToolOutput** | Programmatic Hand-Off | No | Yes (with strict=False) | Strict and tool_choice rejected |
| `litellm` | From config | **ToolOutput** | Programmatic Hand-Off | Proxy-dependent | Yes | Same as upstream provider |

### 6.4 Environment Variable Examples

**Note:** With ADR-001d (Programmatic Hand-Off), the `ORCHESTRATOR_AGENT_PROVIDER` and
`ORCHESTRATOR_AGENT_MODEL` fields are deprecated. The orchestrator no longer makes LLM calls.
Only `LOCATOR_AGENT_PROVIDER` and `LOCATOR_AGENT_MODEL` drive LLM behavior. The examples
below show both fields for backward compatibility (old env files still work).

**OpenAI (current default -- no changes needed):**
```env
LOCATOR_AGENT_PROVIDER=openai
LOCATOR_AGENT_MODEL=gpt-4o-mini
# ORCHESTRATOR_AGENT_PROVIDER=openai  # deprecated, ignored
# ORCHESTRATOR_AGENT_MODEL=gpt-4o-mini  # deprecated, ignored
# STRICT_TOOL_DEFINITIONS=true  (default)
# OUTPUT_MODE=auto  (default)
```

**OpenRouter (recommended for non-OpenAI models):**
```env
LOCATOR_AGENT_PROVIDER=openrouter
LOCATOR_AGENT_MODEL=mistralai/devstral-2512
OPENAI_API_KEY=sk-or-v1-...
# No BASE_URL needed -- OpenRouterProvider handles it
```

**Ollama (local models):**
```env
LOCATOR_AGENT_PROVIDER=ollama
LOCATOR_AGENT_MODEL=qwen3:latest
BASE_URL=http://localhost:11434/v1
STRICT_TOOL_DEFINITIONS=false
# OUTPUT_MODE=auto -> auto-detects Ollama limitations
```

**Ollama with no tool support (e.g., gemma3):**
```env
LOCATOR_AGENT_PROVIDER=ollama
LOCATOR_AGENT_MODEL=gemma3:12b
BASE_URL=http://localhost:11434/v1
STRICT_TOOL_DEFINITIONS=false
OUTPUT_MODE=prompted
```

### 6.5 Backward Compatibility

All new fields have defaults that preserve current behavior:
- `strict_tool_definitions=True` -- same as before (strict inferred)
- `output_mode="auto"` -- NativeOutput for `openai` provider (behavioral change: uses `response_format: json_schema` instead of ToolOutput). This improves reliability for OpenAI but is a different mechanism than before.
- Existing `.env` files with `ORCHESTRATOR_AGENT_PROVIDER="openai"` work unchanged (fields are deprecated but accepted, see section 7.4.7)

---

## 7. ADR-001d: OrchestratorAgent Refactoring (Revised -- Programmatic Hand-Off)

### 7.1 Problem

The OrchestratorAgent uses the `output_type=[function]` pattern (Agent Delegation),
which is the **most fragile pattern** in the codebase:

- Fails on ALL Ollama models (tool result message format rejection)
- Fails on mimo-v2-flash (XML tool call format)
- Requires the model to make a tool call AND the provider to handle the result message

**Programmatic Hand-Off** is the pydantic-ai multi-agent pattern where application code
(not the AI model) decides which agent to call next. The pydantic-ai documentation
explicitly states: "Programmatic agent hand-off is where application code (not the AI
model) decides which agent to call next. This is especially useful when the decision of
which agent to call next is based on deterministic criteria." This is the pattern
recommended for the orchestrator refactoring.

### 7.2 Analysis Against pydantic-ai Multi-Agent Patterns

pydantic-ai documents three multi-agent patterns. Evaluating each against the
OrchestratorAgent's actual behavior reveals a fundamental misalignment.

#### 7.2.1 Pattern 1: Agent Delegation (Current Pattern)

```python
# What pydantic-ai documents:
@parent_agent.tool
async def delegate_task(ctx: RunContext[Deps], args: str) -> result:
    r = await child_agent.run(args, deps=ctx.deps, usage=ctx.usage)
    return r.output
```

The current OrchestratorAgent uses the Agent Delegation pattern via the
`output_type=[function]` mechanism: the LLM "decides" to call
`_get_healed_locators`, which delegates to `locator_agent.heal_async(ctx)`.

**Problem: the delegation adds no value.** The orchestrator's "decision" is
predetermined. Before the LLM even runs, `is_failed_locator_error()` has already
determined whether healing is needed (line 74 of `orchestrator_agent.py`):

```python
if not self._locator_agent.is_failed_locator_error(robot_ctx_payload.error_msg):
    return NoHealingNeededResponse(message=robot_ctx_payload.error_msg)
```

If we reach the LLM call, healing is *always* needed. The LLM has exactly one tool
and must call it. This is a deterministic routing decision masquerading as an
LLM-driven orchestration. The LLM call to the orchestrator agent is wasted tokens.

#### 7.2.2 Pattern 2: Programmatic Hand-Off (Recommended)

```python
# What pydantic-ai documents for deterministic routing:
async def main():
    usage = RunUsage()
    result1 = await agent1.run(prompt, usage=usage)
    if isinstance(result1.output, TypeA):
        result2 = await agent2.run(prompt2, usage=usage)
```

The self-healing system's routing IS deterministic:
1. `is_failed_locator_error()` returns `True` -> call locator agent
2. `is_failed_locator_error()` returns `False` -> return `NoHealingNeededResponse`

No LLM is needed for this decision. This is the textbook case for Programmatic
Hand-Off.

#### 7.2.3 Pattern 3: Graph / Union Output Types (Future Pattern)

```python
# Model chooses output type to signal routing:
agent = Agent(model, output_type=LocatorHealingResponse | TimingHealingResponse | Failed)
```

This pattern is relevant if/when the system expands to multiple healing types where
an LLM must classify the error type. Not applicable to the current single-tool
orchestrator.

### 7.3 Options Evaluated (Revised)

| Option | Description | Compatibility | Complexity | LLM Calls | Quality |
|---|---|---|---|---|---|
| **A** | Keep function tool, add PromptedOutput fallback | Partial | Medium | 2 (orch + locator) | Same |
| **B** | Programmatic Hand-Off: eliminate orchestrator LLM call | **Universal** | **Low** | **1** (locator only) | **Same** |
| **C** | Structured `OrchestratorDecision` output | High | Medium | 2 | Better |
| **D** | Dual-mode: function tool for capable, direct for others | Universal | **High** | 2 or 1 | Same |
| **E** | PromptedOutput always | Universal | Low | 2 | Lower |
| **F** | Tri-mode: function/TextOutput/direct | Universal | **Very High** | 2 or 1 | Same |

**Key insight from pydantic-ai docs**: Options D and F (previous decisions) are over-
engineered. They preserve an LLM call that provides no value -- the orchestrator LLM
call exists only to call a single tool that it MUST call. The pydantic-ai docs are
explicit: when routing is deterministic, use Programmatic Hand-Off, not Agent
Delegation.

**Why this supersedes Option F (Tri-Mode):** Option F preserved the orchestrator LLM
call across three modes (function tool, TextOutput, direct). While TextOutput is a
useful pydantic-ai feature, using it here still costs an LLM call to "decide" what has
already been decided by `is_failed_locator_error()`. The orchestrator's reasoning text
in TextOutput mode is observability theatre -- it cannot change the outcome.

### 7.4 Decision: Option B -- Programmatic Hand-Off

**Revised decision.** Replace the OrchestratorAgent's LLM-based Agent Delegation with
Programmatic Hand-Off. The `OrchestratorAgent` class is retained as a non-LLM
orchestrator that performs deterministic routing and delegates directly to the
locator agent.

#### 7.4.1 Rationale

1. **Routing is deterministic.** `is_failed_locator_error()` is a string-matching
   function, not an LLM inference. The orchestrator LLM call adds latency, cost,
   and failure modes (tool format incompatibility) with zero decision value.

2. **pydantic-ai docs recommend this.** Programmatic Hand-Off is
   explicitly documented for this use case. Using Agent Delegation when routing
   is deterministic is an anti-pattern.

3. **Eliminates ALL provider compatibility issues.** The orchestrator's
   `output_type=[function]` pattern is the single most fragile pattern. Removing it
   eliminates failures on Ollama, mimo-v2-flash, and any provider that does not
   handle tool result messages.

4. **Reduces token usage by ~50%.** Every healing flow currently makes 2 LLM calls
   (orchestrator + locator). With Programmatic Hand-Off, it makes 1 (locator only).

5. **Simplifies codebase.** One code path instead of three (tri-mode). No need for
   orchestrator output mode resolution, `supports_function_output()`, or
   `TextOutput` parsing in the orchestrator.

#### 7.4.2 heal_async() RunContext Decoupling

The current `heal_async()` signature is:

```python
# base_locator_agent.py line 182
async def heal_async(self, ctx: RunContext[PromptPayload]) -> LocatorHealingResponse | str:
```

It takes `RunContext[PromptPayload]` because it was designed to be called from within
the orchestrator's tool function, where pydantic-ai provides a `RunContext`. With
Programmatic Hand-Off, there is no parent agent and thus no `RunContext`.

**However**, `heal_async()` only uses `ctx.deps` (the `PromptPayload`). It passes
`ctx.deps` to `_heal_with_llm()` which passes it as `deps=ctx.deps` to
`self.generation_agent.run()`. The `RunContext` wrapper itself is only used to carry
`PromptPayload` through the call chain.

**Design: Change `heal_async()` to accept `PromptPayload` directly.** The return type
is narrowed to `LocatorHealingResponse` (the `| str` case from
`_catch_token_limit_exceedance` is removed; token limits are now enforced via
`UsageLimits`, which raises `UsageLimitExceeded` as an exception rather than
returning a string).

Current call chain:
```
OrchestratorAgent._get_healed_locators(ctx: RunContext[PromptPayload])
  -> locator_agent.heal_async(ctx)
    -> _heal_with_llm(ctx)
      -> generation_agent.run(deps=ctx.deps)
```

Proposed call chain:
```
OrchestratorAgent.run_async(robot_ctx_payload: PromptPayload)
  -> locator_agent.heal_async(robot_ctx_payload)
    -> _heal_with_llm(robot_ctx_payload)
      -> generation_agent.run(deps=robot_ctx_payload)
```

The `RunContext` dependency was incidental -- it existed because pydantic-ai
injects `RunContext` into tool functions, not because `heal_async()` needed it.

#### 7.4.3 RunUsage Tracking Across Agents

pydantic-ai provides `RunUsage()` for unified token tracking across multiple agent
calls. The orchestrator should create a shared `RunUsage` and pass it to all agent
runs:

```python
from pydantic_ai.usage import RunUsage

class OrchestratorAgent:
    async def run_async(
        self, robot_ctx_payload: PromptPayload
    ) -> LocatorHealingResponse | NoHealingNeededResponse:
        # Shared usage tracker across all agent calls in this healing flow
        usage = RunUsage()

        if not self._locator_agent.is_failed_locator_error(robot_ctx_payload.error_msg):
            return NoHealingNeededResponse(message=robot_ctx_payload.error_msg)

        result = await self._locator_agent.heal_async(
            robot_ctx_payload, usage=usage
        )
        # usage now contains cumulative tokens from all agents
        return result
```

This requires `heal_async()` and its internal methods to accept and forward the
`usage` parameter. See Section 7.4.5 for the full interface design.

#### 7.4.4 Proposed OrchestratorAgent Implementation

```python
# orchestrator_agent.py

from pydantic_ai.usage import RunUsage, UsageLimits
from robot.api import logger as rf_logger

from SelfhealingAgents.self_healing_system.agents.locator_agent.base_locator_agent import (
    BaseLocatorAgent,
)
from SelfhealingAgents.self_healing_system.schemas.api.locator_healing import (
    LocatorHealingResponse,
    NoHealingNeededResponse,
)
from SelfhealingAgents.self_healing_system.schemas.internal_state.prompt_payload import (
    PromptPayload,
)
from SelfhealingAgents.utils.cfg import Cfg
from SelfhealingAgents.utils.logging import log


class OrchestratorAgent:
    """Routes failure payloads to the appropriate healing agent.

    Uses Programmatic Hand-Off (not LLM-based Agent Delegation) because routing
    is deterministic: is_failed_locator_error() decides which path to take.

    Attributes:
        _cfg (Cfg): Application configuration.
        _locator_agent (BaseLocatorAgent): Agent for locator healing.
        _usage_limits (UsageLimits): Token and request limits for child agents.
    """

    def __init__(
        self,
        cfg: Cfg,
        locator_agent: BaseLocatorAgent,
    ) -> None:
        """Initializes the OrchestratorAgent.

        Args:
            cfg: Application configuration. The orchestrator_agent_provider and
                 orchestrator_agent_model fields are preserved for backward
                 compatibility but are no longer used for LLM calls (see
                 Section 7.4.7).
            locator_agent: LocatorAgent instance for handling locator healing.
        """
        self._cfg = cfg
        self._locator_agent: BaseLocatorAgent = locator_agent
        self._usage_limits: UsageLimits = UsageLimits(
            request_limit=cfg.request_limit,
            total_tokens_limit=cfg.total_tokens_limit,
        )

    @log
    async def run_async(
        self, robot_ctx_payload: PromptPayload
    ) -> LocatorHealingResponse | NoHealingNeededResponse:
        """Runs deterministic routing and delegates to the appropriate agent.

        Programmatic Hand-Off pattern: application code decides routing,
        not an LLM. The is_failed_locator_error() check is the routing
        decision.

        Args:
            robot_ctx_payload: Context for the self-healing process.

        Returns:
            LocatorHealingResponse with healing suggestions, or
            NoHealingNeededResponse if the error is not a locator error.
        """
        # Shared usage tracker for all agent calls in this healing flow
        usage = RunUsage()

        # --- Deterministic routing (no LLM needed) ---
        if not self._locator_agent.is_failed_locator_error(
            robot_ctx_payload.error_msg
        ):
            return NoHealingNeededResponse(message=robot_ctx_payload.error_msg)

        # --- Programmatic Hand-Off to locator agent ---
        result = await self._locator_agent.heal_async(
            robot_ctx_payload,
            usage=usage,
            usage_limits=self._usage_limits,
        )

        rf_logger.info(
            f"Healing complete. Total tokens: {usage.total_tokens}",
            also_console=True,
        )

        return result
```

Key changes from current implementation:
- No `Agent` instance, no LLM model, no system prompt, no `output_type`
- No `_get_healed_locators` tool function
- No `_catch_token_limit_exceedance` (token limits enforced via `UsageLimits`)
- Return type narrowed: `LocatorHealingResponse | NoHealingNeededResponse`
  (no more bare `str`)
- `RunUsage` created at the orchestrator level and passed down

#### 7.4.5 Proposed BaseLocatorAgent Interface Changes

```python
# base_locator_agent.py -- changes to heal_async() and _heal_with_llm()

from pydantic_ai.usage import RunUsage, UsageLimits

class BaseLocatorAgent(ABC):

    @log
    async def heal_async(
        self,
        payload: PromptPayload,
        *,
        usage: RunUsage | None = None,
        usage_limits: UsageLimits | None = None,
    ) -> LocatorHealingResponse:
        """Generates suggestions for fixing a broken locator.

        Args:
            payload: The prompt payload containing error context.
            usage: Optional shared RunUsage for cross-agent token tracking.
            usage_limits: Optional usage limits for this agent run.

        Returns:
            LocatorHealingResponse with healing suggestions.
        """
        if self._use_llm_for_locator_generation:
            return await self._heal_with_llm(
                payload, usage=usage, usage_limits=usage_limits
            )
        else:
            return await self._heal_with_dom_utils(payload)

    @log
    async def _heal_with_llm(
        self,
        payload: PromptPayload,
        *,
        usage: RunUsage | None = None,
        usage_limits: UsageLimits | None = None,
    ) -> LocatorHealingResponse:
        """Generates locator suggestions using the LLM approach.

        Args:
            payload: The prompt payload.
            usage: Shared usage tracker.
            usage_limits: Usage limits for this run.

        Returns:
            LocatorHealingResponse with suggestions.
        """
        # Build a synthetic RunContext for prompt generation.
        # PromptsLocatorGenerationAgent.get_user_msg() expects a RunContext.
        ctx = _make_run_context(payload)

        response = await self.generation_agent.run(
            PromptsLocatorGenerationAgent.get_user_msg(ctx),
            deps=payload,
            usage=usage,           # <-- NEW: shared usage tracking
            usage_limits=usage_limits or self._usage_limits,
            model_settings={"temperature": self._cfg.locator_agent_temperature},
        )
        if not isinstance(response.output, LocatorHealingResponse):
            raise ModelRetry(
                "Locator healing response is not of type LocatorHealingResponse."
            )
        return response.output

    @log
    async def _heal_with_dom_utils(
        self, payload: PromptPayload
    ) -> LocatorHealingResponse:
        """Generates locator suggestions using DOM utilities approach.

        Note: _heal_with_dom_utils also needs a RunContext for its prompt
        generation. Same synthetic context approach applies.
        """
        ctx = _make_run_context(payload)
        # ... rest of existing logic, replacing ctx.deps with payload ...


def _make_run_context(payload: PromptPayload) -> RunContext[PromptPayload]:
    """Creates a minimal RunContext wrapper for prompt generation compatibility.

    PromptsLocatorGenerationAgent.get_user_msg() and
    PromptsLocatorSelectionAgent.get_user_msg() expect RunContext[PromptPayload].
    This function bridges the gap during the transition from Agent Delegation
    to Programmatic Hand-Off.

    Long-term, the prompt generation functions should accept PromptPayload
    directly. This helper exists to minimize the blast radius of this
    refactoring.

    Args:
        payload: The prompt payload.

    Returns:
        A RunContext-like object wrapping the payload.
    """
    # RunContext is a dataclass-like object. Creating one outside of
    # pydantic-ai's agent run is not officially supported, but the prompt
    # functions only access ctx.deps, which is all we set here.
    # Alternative: refactor prompt functions to accept PromptPayload directly.
    from types import SimpleNamespace
    return SimpleNamespace(deps=payload)
```

> **Important note on `_make_run_context`**: The `SimpleNamespace` approach is a
> transitional bridge (Phase A). Phase B eliminates it by refactoring prompt generation
> functions to accept `PromptPayload` directly. **Phase B has no committed timeline but
> should be addressed before adding new healing types**, since each new healing type
> would otherwise need its own `_make_run_context`-style bridge. See Section 7.4.8 for
> the phased approach.

#### 7.4.6 Proposed kickoff_multi_agent_system.py Changes

```python
# kickoff_multi_agent_system.py -- minimal changes

class KickoffMultiAgentSystem:
    @staticmethod
    @log
    def kickoff_healing(
        data: running.Keyword,
        result: result.Keyword,
        *,
        cfg: Cfg,
        tried_locator_memory: List[str],
    ) -> LocatorHealingResponse | NoHealingNeededResponse:
        # NOTE: return type narrows from
        #   LocatorHealingResponse | str | NoHealingNeededResponse
        # to
        #   LocatorHealingResponse | NoHealingNeededResponse
        # The bare str case came from _catch_token_limit_exceedance which
        # is removed. Token limits are now enforced via UsageLimits, which
        # raises UsageLimitExceeded (an exception, not a str return).

        agent_type = _LIBRARY_MAPPING.get(result.owner, None)
        if agent_type is None:
            raise ValueError(f"Library type: {agent_type} not supported.")

        dom_utility = DomUtilityFactory.create_dom_utility(agent_type)
        robot_ctx_payload = RobotCtxRetriever.get_context_payload(
            data, result, dom_utility
        )
        robot_ctx_payload.tried_locator_memory = tried_locator_memory
        robot_ctx_payload.locator_type = cfg.locator_type

        locator_agent = LocatorAgentFactory.create_agent(
            agent_type, cfg, dom_utility
        )

        # OrchestratorAgent no longer creates an LLM agent internally.
        # It only needs cfg and locator_agent for deterministic routing.
        orchestrator_agent = OrchestratorAgent(cfg, locator_agent)

        response = asyncio.get_event_loop().run_until_complete(
            orchestrator_agent.run_async(robot_ctx_payload)
        )
        return response
```

#### 7.4.7 Backward Compatibility: Cfg Fields

The `Cfg` class currently has three orchestrator-specific fields:
- `orchestrator_agent_provider`
- `orchestrator_agent_model`
- `orchestrator_agent_temperature`

With Programmatic Hand-Off, the orchestrator no longer makes LLM calls. These fields
become unused. However, removing them would break existing `.env` files that set
`ORCHESTRATOR_AGENT_PROVIDER`, `ORCHESTRATOR_AGENT_MODEL`, or
`ORCHESTRATOR_AGENT_TEMPERATURE`.

**Design: Keep the fields, mark as deprecated.**

```python
# In Cfg -- no changes to field definitions, but update descriptions:
orchestrator_agent_provider: str = Field(
    "openai", env="ORCHESTRATOR_AGENT_PROVIDER",
    description=(
        "DEPRECATED: No longer used. The orchestrator now uses programmatic "
        "routing instead of LLM-based delegation. Kept for backward "
        "compatibility with existing .env files. Will be removed in v2.0."
    ),
)
orchestrator_agent_model: str = Field(
    "gpt-4o-mini", env="ORCHESTRATOR_AGENT_MODEL",
    description=(
        "DEPRECATED: No longer used. See orchestrator_agent_provider."
    ),
)
orchestrator_agent_temperature: float = Field(
    0.1, gt=0, env="ORCHESTRATOR_AGENT_TEMPERATURE",
    description=(
        "DEPRECATED: No longer used. See orchestrator_agent_provider."
    ),
)
```

Since `Cfg` uses `extra="forbid"` (confirmed at `cfg.py` line 13:
`model_config = ConfigDict(frozen=True, extra="forbid")`), keeping the fields
prevents validation errors when existing `.env` files provide them. Any environment
variable not matching a declared field would cause a `ValidationError`.

#### 7.4.8 Phased RunContext Elimination

The `_make_run_context` bridge from Section 7.4.5 is a transitional measure. The
full elimination of `RunContext` from the locator agent's public API should proceed
in phases:

**Phase A (this ADR):**
- `heal_async()` accepts `PromptPayload` directly
- Internal methods use `_make_run_context()` bridge for prompt generation
- Prompt functions unchanged

**Phase B (follow-up -- no committed timeline, should precede new healing types):**
- `PromptsLocatorGenerationAgent.get_user_msg(ctx)` refactored to
  `get_user_msg(payload: PromptPayload)`
- `PromptsLocatorSelectionAgent.get_user_msg(ctx, ...)` refactored similarly
- `_make_run_context()` bridge removed
- `validate_output` handler updated to receive `PromptPayload` in deps

Phase B is a clean, low-risk refactoring because:
- The prompt functions only access `ctx.deps.*` attributes
- The `validate_output` handler receives `RunContext` from pydantic-ai's internal
  machinery (via `generation_agent.run(deps=payload)`), not from external callers
- The change is purely mechanical: replace `ctx.deps.X` with `payload.X`

### 7.5 Future: When LLM-Based Orchestration IS Needed

The Programmatic Hand-Off pattern is correct for the current single-tool system.
However, as the system grows, LLM-based orchestration becomes valuable. This section
documents when to reintroduce it and which pydantic-ai patterns to use.

#### 7.5.1 When Agent Delegation Becomes Appropriate

Agent Delegation (Pattern 1) becomes valuable when:
- Multiple healing types exist (locator, timing, assertion, API)
- Error classification is ambiguous (the error message alone is not sufficient)
- The orchestrator needs to reason about WHICH agent to call

Example future state:
```
Error: "Element not found" -> clearly locator -> deterministic
Error: "Timeout waiting for element" -> locator or timing? -> needs LLM
Error: "Expected 'OK' but got '500'" -> assertion or API? -> needs LLM
```

#### 7.5.2 Union Output Types for Multi-Agent Routing

When multiple healing types exist, the orchestrator can use union output types
to classify errors and signal which agent should handle them:

```python
from pydantic_ai import Agent

class LocatorHealingRequest(BaseModel):
    """Signal to route to the locator agent."""
    failed_locator: str
    dom_context: str

class TimingHealingRequest(BaseModel):
    """Signal to route to the timing agent."""
    timeout_ms: int
    suggested_wait_ms: int

class NoHealingNeeded(BaseModel):
    """Signal that no healing is applicable."""
    reason: str

# Future orchestrator with LLM-based routing:
orchestrator_agent = Agent(
    model=get_client_model(...),
    output_type=LocatorHealingRequest | TimingHealingRequest | NoHealingNeeded,
    system_prompt="Classify the error and decide which healing agent to invoke.",
)

async def run_healing(payload: PromptPayload) -> HealingResponse:
    usage = RunUsage()
    decision = await orchestrator_agent.run(
        build_prompt(payload), usage=usage
    )

    match decision.output:
        case LocatorHealingRequest() as req:
            return await locator_agent.heal_async(payload, usage=usage)
        case TimingHealingRequest() as req:
            return await timing_agent.heal_async(payload, usage=usage)
        case NoHealingNeeded() as req:
            return NoHealingNeededResponse(message=req.reason)
```

This is a hybrid of Programmatic Hand-Off and union output types: the LLM classifies,
then application code routes. The LLM does NOT call tools -- it returns a typed
decision struct, and the application dispatches.

#### 7.5.3 TextOutput for Lightweight Classification

For simpler classification scenarios where a full structured output type is
overkill, pydantic-ai's `TextOutput(function)` pattern can be used:

```python
from pydantic_ai.output import TextOutput

def parse_healing_decision(text: str) -> str:
    """Extract the healing type from free-form LLM text.

    Returns one of: 'locator', 'timing', 'assertion', 'none'.
    """
    text_lower = text.lower()
    if "locator" in text_lower or "element not found" in text_lower:
        return "locator"
    elif "timeout" in text_lower or "timing" in text_lower:
        return "timing"
    elif "assertion" in text_lower or "expected" in text_lower:
        return "assertion"
    return "none"

# Agent that returns text, processed by a function:
classifier = Agent(
    model=get_client_model(...),
    output_type=TextOutput(parse_healing_decision),
    system_prompt="Classify this error type. Respond with one word.",
)
```

This is lighter than structured output: the model returns free text, the function
parses it deterministically. Useful as a stepping stone before committing to full
structured classification.

#### 7.5.4 Message History for Multi-Turn Healing

When a healing attempt fails and the system retries, pydantic-ai's message history
preserves the conversation state:

```python
# First attempt:
result1 = await locator_agent.generation_agent.run(
    prompt, deps=payload, usage=usage
)

# If validation fails, retry with history:
result2 = await locator_agent.generation_agent.run(
    "The previous suggestions were invalid. Try different locators.",
    deps=payload,
    usage=usage,
    message_history=result1.all_messages(
        output_tool_return_content="Previous suggestions failed validation."
    ),
)
```

This is already partially implemented via pydantic-ai's built-in `ModelRetry`
mechanism in `validate_output`. The explicit message history API provides more
control for future multi-turn healing flows.

### 7.6 Impact on Other ADR Sections

#### 7.6.1 ADR-001b (Output Strategy) -- Simplified

With the orchestrator no longer using the `output_type=[function]` pattern, the following
functions in `output_strategy.py` are no longer needed by the orchestrator and
should be removed:

- `resolve_orchestrator_output_mode()` -- the orchestrator makes no LLM calls
- `supports_function_output()` -- no Agent Delegation in the orchestrator
- The TextOutput-based orchestrator fallback -- unnecessary (see section 5.5.4)

The output strategy module only needs `resolve_structured_output_type()` and
`make_prepare_tools_hook()` for the locator agent.

#### 7.6.2 ADR-001c (Configuration) -- Simplified

The `orchestrator_agent_provider` / `orchestrator_agent_model` fields no longer
drive LLM behavior. The critical provider configuration shifts entirely to
`locator_agent_provider` / `locator_agent_model`.

#### 7.6.3 ADR-001f (Advanced Tool Features) -- Impact

With Programmatic Hand-Off, the `_get_healed_locators` tool function no longer
exists. This affects ADR-001f as follows:

- **`tool_timeout` (Section 13.7):** No longer needed for the orchestrator. The
  orchestrator has no tools. The locator agent uses `output_type` (not tools), so
  `tool_timeout` does not apply. The `TOOL_TIMEOUT` Cfg field can be deferred.
- **Per-tool `prepare` (Section 13.4):** Still not needed (no tools in orchestrator).
- **`ToolReturn` (Section 13.6):** No longer applicable (no tool function to return from).
- **`prepare_tools` hooks (Sections 13.2-13.3):** Still needed for the locator agent's
  generation agent, which uses ToolOutput for structured output. The deep schema
  sanitization (`_inline_refs`, `_simplify_array_items`) remains valid.

### 7.7 File Changes

| File | Change Type | Description |
|------|------------|-------------|
| `orchestrator_agent.py` | MODIFY | Remove Agent/LLM, implement Programmatic Hand-Off |
| `base_locator_agent.py` | MODIFY | Change `heal_async(ctx)` to `heal_async(payload, usage=, usage_limits=)` |
| `base_locator_agent.py` | MODIFY | Add `_make_run_context()` bridge for prompt compat |
| `kickoff_multi_agent_system.py` | MODIFY | Narrow return type annotation |
| `self_healing_engine.py` | VERIFY | No code changes; `_initiate_healing` checks `isinstance(LocatorHealingResponse)` which still works |
| `cfg.py` | MODIFY | Update descriptions to mark orchestrator fields as deprecated |
| `output_strategy.py` | MODIFY | Remove orchestrator-specific functions |

### 7.8 Comparison: Previous Decisions (Options D, F) vs Revised (Option B)

| Dimension | Option D (Dual-Mode) | Option F (Tri-Mode) | Option B (Programmatic Hand-Off) |
|---|---|---|---|
| LLM calls per healing | 2 | 2 or 1 | **1** |
| Code paths | 2 | 3 | **1** |
| Provider compatibility | Universal (via branching) | Universal (via branching) | **Universal** (no LLM in orchestrator) |
| Token cost | Higher (~50% overhead) | Higher (~50% overhead) | **Lower** |
| Latency | Higher (extra LLM round-trip) | Higher (extra LLM round-trip) | **Lower** |
| `output_strategy.py` dependency | Yes | Yes (3 functions) | **No** |
| pydantic-ai alignment | Agent Delegation (misuse) | Agent Delegation (misuse) | **Programmatic Hand-Off** (recommended) |
| Future extensibility | Must refactor for multi-agent | Must refactor for multi-agent | **Clean foundation** for union output types |
| Backward compat | Full | Full | **Full** (Cfg fields preserved) |

### 7.9 Risk Analysis for Option B

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Prompt functions depend on RunContext internals beyond `.deps` | Low | Medium | `_make_run_context` bridge; audit all `.get_user_msg()` calls |
| `_catch_token_limit_exceedance` removal misses error cases | Low | Low | `UsageLimits` raises `UsageLimitExceeded` exception instead |
| Users depend on orchestrator LLM call for logging/observability | Low | Low | Add logging to orchestrator's deterministic routing path |
| `heal_async` signature change breaks subclass overrides | Medium | Medium | Only `BaseLocatorAgent` defines it; check all concrete subclasses |
| Deprecating Cfg fields confuses users | Low | Low | Clear deprecation message; no functional change |

---

## 8. ADR-001e: Schema Improvements

### 8.1 Decision

Type the `LocatorHealingResponse` list fields for better model behavior and validation.

### 8.2 Current Schema

```python
class LocatorHealingResponse(BaseModel):
    suggestions: list = Field(...)       # -> "items": {} (accepts anything)
    metadata: list = Field(default=[])   # -> "items": {} (accepts anything)
```

### 8.3 Proposed Schema

```python
class LocatorHealingResponse(BaseModel):
    suggestions: list[str] = Field(
        ..., description="Suggestions for fixing locator error."
    )
    metadata: list[dict] = Field(
        default=[], description="Metadata about each locator suggestion."
    )
```

### 8.4 Rationale

- **Better output quality**: Experiments showed typed `list[str]` produced richer,
  more consistent output (models populate metadata with useful descriptions)
- **Better JSON schema**: `"items": {"type": "string"}` gives the model a clear
  constraint instead of the ambiguous `"items": {}`
- **Better validation**: Pydantic will catch type mismatches at deserialization time
- **One known regression**: minimax-m2.1 on OpenRouter fails with typed `list[str]`
  (returns text instead of tool call). This model works with `OpenRouterProvider`
  or with untyped fields. Since `OpenRouterProvider` is the recommended path for
  OpenRouter, this is acceptable.

### 8.5 Impact on Existing Code

The `_process_locator()` method in `base_locator_agent.py` already expects `str` items.
The `validate_output` handler iterates `output.suggestions` and calls
`self._process_locator(x)` on each. Typing `list[str]` formalizes the existing contract.

### 8.6 File Changes

| File | Change Type | Description |
|------|------------|-------------|
| `schemas/api/locator_healing.py` | MODIFY | Type `list` -> `list[str]` and `list` -> `list[dict]` |

---

## 9. Implementation Plan

### 9.1 Phase 1: Foundation (Provider + Config)

**Priority: CRITICAL**

Changes that enable all subsequent work:

| Step | File | Action |
|------|------|--------|
| 1.1 | `cfg.py` | Add `strict_tool_definitions` and `output_mode` fields |
| 1.2 | `providers/openai_builder.py` | Add profile, migrate to `OpenAIChatModel` |
| 1.3 | `providers/azure_builder.py` | Migrate to `OpenAIChatModel` |
| 1.4 | `providers/litellm_builder.py` | Fix double-path bug, add profile, migrate |
| 1.5 | `providers/openrouter_builder.py` | CREATE -- new builder using `OpenRouterProvider` |
| 1.6 | `providers/ollama_builder.py` | CREATE -- new builder with `strict=False` |
| 1.7 | `model_factory.py` | Update type hint to `OpenAIChatModel` |
| 1.8 | `client_model.py` | Update type hint to `OpenAIChatModel` |
| 1.9 | `pyproject.toml` | Add `openrouter` and `ollama` entry points |

### 9.2 Phase 2: Output Strategy + Orchestrator Refactoring (Revised)

**Priority: HIGH**

| Step | File | Action |
|------|------|--------|
| 2.1 | `llm/output_strategy.py` | CREATE -- tri-modal output selection, prepare_tools hooks, PromptedOutput template (locator agents only). Include `_inline_refs`, `_resolve_refs_recursive`, and `_simplify_array_items` schema sanitization functions (section 13.3) |
| 2.2 | `agents/locator_agent/base_locator_agent.py` | Integrate `resolve_structured_output_type()` + `make_prepare_tools_hook()`; change `heal_async()` signature to accept `PromptPayload` directly (see section 7.4.5); add `_make_run_context` bridge for backward-compatible prompt generation |
| 2.3 | `agents/orchestrator_agent/orchestrator_agent.py` | REFACTOR: Replace LLM-based agent with Programmatic Hand-Off (see section 7.4.4). Remove Agent/model creation, keep deterministic `is_failed_locator_error()` routing + `RunUsage` tracking |
| 2.4 | `kickoff_multi_agent_system.py` | MODIFY: Narrow return type from `LocatorHealingResponse | str | NoHealingNeededResponse` to `LocatorHealingResponse | NoHealingNeededResponse` |

### 9.3 Phase 3: Schema

**Priority: MEDIUM**

| Step | File | Action |
|------|------|--------|
| 3.1 | `schemas/api/locator_healing.py` | Type `list` -> `list[str]`, `list` -> `list[dict]` |

### 9.4 Phase 4: Testing & Validation

**Priority: HIGH (parallel with phases 1-3)**

| Step | Action |
|------|--------|
| 4.1 | Unit tests for each builder (mock providers), including Azure builder |
| 4.2 | Unit tests for `output_strategy.py` |
| 4.3 | Unit tests for OrchestratorAgent Programmatic Hand-Off |
| 4.4 | Integration tests against OpenRouter (devstral) |
| 4.5 | Integration tests against Ollama (qwen3, gemma3) |
| 4.6 | Backward compatibility test (existing .env) |
| 4.7 | Unit tests for `_inline_refs` and `_simplify_array_items` schema sanitization |
| 4.8 | Integration tests against Azure, LiteLLM, vLLM (see compatibility matrix 10.3) |

### 9.5 Phase 5: Multi-Healing Type Foundation

**Priority: LOW (future work)**

This phase covers the unified delivery plan for extensible healing types, designed in
sections 14-16 (ADR-001g, ADR-001h, ADR-001i). It is not part of the initial
non-OpenAI compatibility release but is listed here to establish the dependency chain.

| Step | Action |
|------|--------|
| 5.1 | Define `HealingType` enum and `ErrorClassifier` module (section 14, 15) |
| 5.2 | Implement healing-type-specific agent registry (section 14) |
| 5.3 | Extend orchestrator with hybrid routing for multi-healing types (section 15) |
| 5.4 | Add context enrichment pipeline and DDD expansion (section 16) |

**Prerequisite:** Phases 1-4 must be complete. The multi-healing architecture builds
on the provider abstraction, output strategy, and Programmatic Hand-Off patterns
established in phases 1-3.

### 9.6 Dependency Graph

```
Phase 1 (Foundation)
  ├── 1.1 cfg.py
  ├── 1.2-1.4 Modify existing builders  ─── depends on 1.1
  ├── 1.5-1.6 Create new builders       ─── depends on 1.1
  ├── 1.7-1.8 Update type hints         ─── depends on 1.2-1.6
  └── 1.9 pyproject.toml               ─── depends on 1.5-1.6

Phase 2 (Output Strategy) ─── depends on Phase 1
  ├── 2.1 output_strategy.py           ─── depends on 1.1
  │     includes _inline_refs, _simplify_array_items (section 13.3)
  ├── 2.2 base_locator_agent.py        ─── depends on 2.1
  │     includes heal_async() signature change + _make_run_context bridge (section 7.4.5)
  ├── 2.3 orchestrator_agent.py        ─── depends on 2.2 (heal_async signature)
  └── 2.4 kickoff_multi_agent_system.py ─── depends on 2.3

Phase 3 (Schema) ─── independent, can run in parallel
  └── 3.1 locator_healing.py

Phase 4 (Testing) ─── parallel with all phases
  ├── 4.1-4.3 Unit tests               ─── after each phase
  ├── 4.7 Schema sanitization tests    ─── after 2.1
  └── 4.4-4.6, 4.8 Integration tests  ─── after all phases

Phase 5 (Multi-Healing Foundation) ─── depends on Phases 1-4
  ├── 5.1-5.2 Healing types + registry ─── sections 14-16
  ├── 5.3 Hybrid routing              ─── section 15
  └── 5.4 Context enrichment          ─── section 16
```

---

## 10. Testing Strategy

### 10.1 Unit Tests

#### 10.1.1 Builder Tests

Location: `tests/unit/llm/providers/`

```python
# test_openai_builder.py
def test_openai_builder_creates_chat_model():
    """Verify OpenAIChatModel is returned, not deprecated OpenAIModel."""

def test_openai_builder_applies_profile():
    """Verify profile is set with strict_tool_definitions from config."""

def test_openai_builder_strict_false():
    """Verify strict=False when cfg.strict_tool_definitions=False."""

# test_azure_builder.py
def test_azure_builder_creates_chat_model():
    """Verify OpenAIChatModel is returned with Azure endpoint configuration."""

def test_azure_builder_applies_profile():
    """Verify profile is set with strict_tool_definitions from config."""

def test_azure_builder_uses_azure_base_url():
    """Verify Azure-specific base URL is passed to the model."""

def test_azure_builder_strict_false():
    """Verify strict=False when cfg.strict_tool_definitions=False."""

def test_azure_builder_api_version_forwarded():
    """Verify Azure API version is correctly forwarded to the provider."""

# test_openrouter_builder.py
def test_openrouter_builder_uses_openrouter_provider():
    """Verify OpenRouterProvider is used, not OpenAIProvider."""

# test_ollama_builder.py
def test_ollama_builder_strict_false_by_default():
    """Verify strict is always False for Ollama."""

def test_ollama_builder_default_base_url():
    """Verify default localhost:11434 when no BASE_URL configured."""

# test_litellm_builder.py
def test_litellm_builder_no_double_path():
    """Verify base_url is passed as-is, no /v1/chat/completions appended."""
```

#### 10.1.2 Output Strategy Tests (Revised)

Location: `tests/unit/llm/`

```python
# test_output_strategy.py

# --- resolve_structured_output_type ---

def test_auto_mode_returns_native_output_for_openai():
    """Auto mode returns NativeOutput for OpenAI provider."""

def test_auto_mode_returns_native_output_for_azure():
    """Auto mode returns NativeOutput for Azure provider."""

def test_auto_mode_returns_schema_for_openrouter():
    """Auto mode returns raw schema class (ToolOutput) for OpenRouter."""

def test_auto_mode_returns_schema_for_ollama():
    """Auto mode returns raw schema class (ToolOutput) for Ollama with tools."""

def test_prompted_mode_returns_prompted_output_with_template():
    """Prompted mode wraps in PromptedOutput with locator healing template."""

def test_native_mode_returns_native_output():
    """Native mode always wraps in NativeOutput regardless of provider."""

def test_tool_mode_returns_raw_schema():
    """Tool mode always returns raw schema class."""

def test_text_mode_falls_back_to_prompted_output_with_log(caplog):
    """Text mode resolves to PromptedOutput and emits a deprecation/info log.

    The 'text' output mode is a convenience alias. Internally it resolves
    to PromptedOutput because the agent still needs structured data. The
    log message informs the user that 'text' is equivalent to 'prompted'.
    """

def test_prompted_output_template_contains_schema_placeholder():
    """PromptedOutput template must contain {schema} placeholder."""

def test_prompted_output_template_mentions_locators():
    """PromptedOutput template must contain domain-specific locator guidance."""

# --- resolve_orchestrator_output_mode (REMOVED per ADR-001d) ---
# These tests are no longer needed. The orchestrator uses Programmatic Hand-Off
# and does not call any output mode resolution functions.
# See tests/unit/agents/test_orchestrator_agent.py for orchestrator tests.

# --- make_prepare_tools_hook ---

def test_prepare_tools_hook_none_for_openai():
    """No prepare_tools hook needed for OpenAI."""

def test_prepare_tools_hook_none_for_openrouter():
    """No prepare_tools hook needed for OpenRouter."""

def test_prepare_tools_hook_returns_callable_for_ollama():
    """Ollama gets a prepare_tools hook that strips strict artifacts."""

def test_prepare_tools_hook_returns_callable_for_vllm():
    """vLLM gets a prepare_tools hook that strips strict fields."""

async def test_ollama_prepare_tools_strips_strict():
    """Ollama hook removes 'strict' and 'additionalProperties' from schemas."""

async def test_ollama_prepare_tools_strips_nested_strict():
    """Ollama hook recurses into nested properties and items."""

async def test_vllm_prepare_tools_strips_strict():
    """vLLM hook removes 'strict' from schemas."""
```

#### 10.1.3 OrchestratorAgent Tests (Revised -- Programmatic Hand-Off)

Location: `tests/unit/agents/`

```python
# test_orchestrator_agent.py

# --- Deterministic routing (no LLM) ---

def test_orchestrator_routes_locator_error_to_heal_async():
    """Verify is_failed_locator_error() == True routes to locator_agent.heal_async()."""

def test_orchestrator_returns_no_healing_for_non_locator_error():
    """Verify NoHealingNeededResponse when is_failed_locator_error() == False."""

def test_orchestrator_no_llm_call():
    """Verify no Agent is created, no model.run() is called."""

# --- heal_async integration ---

def test_orchestrator_passes_prompt_payload_to_heal_async():
    """Verify PromptPayload (not RunContext) is passed to locator_agent.heal_async()."""

def test_orchestrator_passes_usage_to_heal_async():
    """Verify RunUsage object is forwarded to heal_async for token tracking."""

def test_orchestrator_passes_usage_limits_to_heal_async():
    """Verify UsageLimits object is forwarded to heal_async."""

# --- RunUsage tracking ---

def test_orchestrator_returns_run_usage():
    """Verify orchestrator returns RunUsage from locator_agent."""

def test_orchestrator_run_usage_zero_when_no_healing():
    """Verify RunUsage has zero tokens when NoHealingNeededResponse returned."""

# --- PromptPayload construction ---

def test_orchestrator_builds_prompt_payload_from_keyword_data():
    """Verify PromptPayload is correctly assembled from keyword data and result."""

def test_orchestrator_includes_tried_locator_memory():
    """Verify tried_locator_memory is passed through to PromptPayload."""

# --- Backward compatibility ---

def test_orchestrator_ignores_orchestrator_provider_config():
    """Verify orchestrator_agent_provider config field is not used."""

def test_orchestrator_ignores_orchestrator_model_config():
    """Verify orchestrator_agent_model config field is not used."""
```

#### 10.1.4 Schema Tests

Location: `tests/unit/schemas/`

```python
# test_locator_healing.py
def test_typed_suggestions_rejects_non_strings():
    """Verify list[str] rejects non-string elements."""

def test_typed_metadata_accepts_dicts():
    """Verify list[dict] accepts dict elements."""

def test_schema_generates_items_type_string():
    """Verify JSON schema has items.type = 'string' for suggestions."""
```

#### 10.1.5 Negative Tests

Location: `tests/unit/llm/`

```python
# test_output_strategy_negative.py

def test_ollama_auto_mode_non_tool_capable_model_raises_or_falls_back():
    """Verify that auto mode with Ollama + a model that lacks tool support
    (e.g., gemma3 without tool-calling) either:
    - Falls back to PromptedOutput with a warning log, OR
    - Raises a clear error directing the user to set OUTPUT_MODE=prompted.

    This ensures users do not silently get broken tool-mode output from
    models that cannot produce function calls.
    """
```

### 10.2 Integration Tests

Location: `tests/integration/`

#### 10.2.1 OpenRouter Integration

```python
# test_openrouter_integration.py
@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY") and not os.getenv("OPENAI_API_KEY"),
    reason="No OpenRouter API key (set OPENROUTER_API_KEY or OPENAI_API_KEY with an OpenRouter key)",
)
class TestOpenRouterIntegration:
    async def test_locator_healing_with_devstral(self):
        """End-to-end test with devstral-2512 via OpenRouter."""

    async def test_orchestrator_programmatic_handoff(self):
        """Verify OrchestratorAgent Programmatic Hand-Off routes to locator agent on OpenRouter."""

    async def test_openrouter_provider_all_output_modes(self):
        """Test tool, prompted, and auto output modes."""
```

#### 10.2.2 Ollama Integration

```python
# test_ollama_integration.py
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OLLAMA_BASE_URL"), reason="No Ollama")
class TestOllamaIntegration:
    async def test_locator_healing_prompted_output(self):
        """Verify PromptedOutput works with Ollama models."""

    async def test_orchestrator_programmatic_handoff_ollama(self):
        """Verify OrchestratorAgent Programmatic Hand-Off routes to locator agent on Ollama."""

    async def test_qwen3_structured_output(self):
        """Verify qwen3 tool-based structured output works."""
```

#### 10.2.3 Azure Integration

```python
# test_azure_integration.py
@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("AZURE_OPENAI_API_KEY"),
    reason="No Azure OpenAI API key",
)
class TestAzureIntegration:
    async def test_locator_healing_with_azure_gpt4o(self):
        """End-to-end test with gpt-4o-mini via Azure OpenAI."""

    async def test_azure_native_output_mode(self):
        """Verify NativeOutput (structured output) works with Azure."""

    async def test_azure_tool_output_mode(self):
        """Verify ToolOutput works with Azure."""
```

#### 10.2.4 LiteLLM Integration

```python
# test_litellm_integration.py
@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("LITELLM_BASE_URL"),
    reason="No LiteLLM proxy available",
)
class TestLiteLLMIntegration:
    async def test_locator_healing_via_litellm_proxy(self):
        """End-to-end test with a model proxied through LiteLLM."""

    async def test_litellm_no_double_path_bug(self):
        """Verify the double-path bug fix: base_url is not appended with /v1/chat/completions."""

    async def test_litellm_prompted_output(self):
        """Verify PromptedOutput works through LiteLLM proxy."""
```

#### 10.2.5 vLLM Integration

```python
# test_vllm_integration.py
@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("VLLM_BASE_URL"),
    reason="No vLLM server available",
)
class TestVLLMIntegration:
    async def test_locator_healing_via_vllm(self):
        """End-to-end test with a model served by vLLM.

        Note: When LOCATOR_AGENT_PROVIDER='openai' (the current recommended
        config for vLLM), the vLLM-specific prepare_tools hook does NOT
        activate. Schema sanitization only occurs when provider='vllm'.
        Until a vllm builder entry point is added, users needing schema
        sanitization should use OUTPUT_MODE=prompted as a workaround.
        """

    async def test_vllm_prompted_output_workaround(self):
        """Verify PromptedOutput works with vLLM as a prepare_tools gap workaround."""
```

#### 10.2.6 Backward Compatibility

```python
# test_backward_compat.py
class TestBackwardCompatibility:
    def test_default_config_unchanged(self):
        """Verify default Cfg values match previous behavior."""

    def test_openai_provider_default_strict_true(self):
        """Verify OpenAI builder defaults to strict=True."""

    async def test_existing_env_still_works(self):
        """Verify existing .env with ORCHESTRATOR_AGENT_PROVIDER=openai works."""
```

### 10.3 Compatibility Matrix Test

Location: `tests/integration/test_compatibility_matrix.py`

Parameterized test that runs the same prompt against multiple provider/model combinations:

```python
@pytest.mark.parametrize("provider,model,skip_reason", [
    ("openai", "gpt-4o-mini", None),
    ("azure", "gpt-4o-mini", "AZURE_OPENAI_API_KEY"),
    ("openrouter", "mistralai/devstral-2512", "OPENROUTER_API_KEY"),
    ("openrouter", "qwen/qwen3-coder-next", "OPENROUTER_API_KEY"),
    ("ollama", "qwen3:latest", "OLLAMA_BASE_URL"),
    ("litellm", "gpt-4o-mini", "LITELLM_BASE_URL"),
    ("vllm", "meta-llama/Llama-3-8B", "VLLM_BASE_URL"),
])
async def test_locator_healing(provider, model, skip_reason):
    """Verify locator healing works across all supported configurations.

    Each row is skipped if the required environment variable is not set.
    For providers using OPENAI_API_KEY as fallback (e.g., OpenRouter
    via the openai builder), the skip_reason column names the preferred
    env var. The test fixture resolves the actual key at runtime.
    """
```

### 10.4 Test Infrastructure

- **Mocking**: Use `unittest.mock.patch` for provider builders in unit tests
- **Fixtures**: Shared `Cfg` fixtures with different provider configurations
- **Markers**: `@pytest.mark.integration` for tests requiring live API access
- **CI**: Integration tests run in a separate CI job with secrets

---

## 11. Migration Guide

**Important:** With the Programmatic Hand-Off decision (section 7.4.4), the `ORCHESTRATOR_AGENT_PROVIDER`
and `ORCHESTRATOR_AGENT_MODEL` fields are deprecated but still accepted (no validation error).
Only `LOCATOR_AGENT_PROVIDER` and `LOCATOR_AGENT_MODEL` control LLM behavior. The examples
below show both old and new configurations.

**Deprecation log behavior:** When deprecated orchestrator fields (`ORCHESTRATOR_AGENT_PROVIDER`,
`ORCHESTRATOR_AGENT_MODEL`) are set in the environment, the system emits a `DeprecationWarning`
log at startup. The fields are silently ignored at runtime (the orchestrator uses Programmatic
Hand-Off regardless). Users should remove these fields from their `.env` to suppress the warning.

**Rollback:** If any migration step causes issues, see section 12.2 for the rollback strategy.

### 11.1 For Existing OpenAI Users

**No changes required.** All defaults preserve current behavior. Existing `.env` files
with `ORCHESTRATOR_AGENT_PROVIDER` will not break -- the fields are silently ignored
(with a deprecation log).

### 11.2 For Azure Users

**Before** (using `openai` provider with Azure endpoint):
```env
ORCHESTRATOR_AGENT_PROVIDER="openai"        # deprecated, ignored
ORCHESTRATOR_AGENT_MODEL="gpt-4o-mini"      # deprecated, ignored
LOCATOR_AGENT_PROVIDER="openai"
LOCATOR_AGENT_MODEL="gpt-4o-mini"
BASE_URL=https://my-resource.openai.azure.com/openai/deployments/gpt-4o-mini
OPENAI_API_KEY=your-azure-api-key
```

**After** (using dedicated `azure` provider):
```env
LOCATOR_AGENT_PROVIDER="azure"
LOCATOR_AGENT_MODEL="gpt-4o-mini"
AZURE_OPENAI_API_KEY=your-azure-api-key
AZURE_OPENAI_ENDPOINT=https://my-resource.openai.azure.com
# BASE_URL no longer needed -- Azure builder handles endpoint construction
# ORCHESTRATOR_AGENT_* fields no longer needed
```

The old configuration continues to work but the `azure` provider is recommended for
proper Azure authentication and endpoint handling.

### 11.3 For OpenRouter Users (Current Workaround)

**Before** (using `openai` provider with `BASE_URL`):
```env
ORCHESTRATOR_AGENT_PROVIDER="openai"        # deprecated, ignored
ORCHESTRATOR_AGENT_MODEL="mistralai/devstral-2512"  # deprecated, ignored
LOCATOR_AGENT_PROVIDER="openai"
LOCATOR_AGENT_MODEL="mistralai/devstral-2512"
BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY=sk-or-v1-...
```

**After** (using dedicated `openrouter` provider):
```env
LOCATOR_AGENT_PROVIDER="openrouter"
LOCATOR_AGENT_MODEL="mistralai/devstral-2512"
OPENAI_API_KEY=sk-or-v1-...
# BASE_URL no longer needed -- OpenRouterProvider handles it
# ORCHESTRATOR_AGENT_* fields no longer needed
```

The old configuration continues to work but the new `openrouter` provider is recommended.

### 11.4 For LiteLLM Users

**Before** (double-path bug present):
```env
LOCATOR_AGENT_PROVIDER="litellm"
LOCATOR_AGENT_MODEL="gpt-4o-mini"
BASE_URL=http://litellm-proxy:4000/v1
```

In previous versions, the LiteLLM builder appended `/v1/chat/completions` to the
`BASE_URL`, resulting in a malformed URL like `http://litellm-proxy:4000/v1/v1/chat/completions`.
Users had to work around this by omitting `/v1` from their `BASE_URL`.

**After** (double-path bug fixed):
```env
LOCATOR_AGENT_PROVIDER="litellm"
LOCATOR_AGENT_MODEL="gpt-4o-mini"
BASE_URL=http://litellm-proxy:4000/v1
```

The `BASE_URL` is now passed as-is to the provider. **If you previously omitted `/v1` as a
workaround, you must add it back.** The standard LiteLLM proxy URL includes `/v1`.

### 11.5 For New Ollama Users

```env
LOCATOR_AGENT_PROVIDER="ollama"
LOCATOR_AGENT_MODEL="qwen3:latest"
BASE_URL=http://localhost:11434/v1
STRICT_TOOL_DEFINITIONS=false
# OUTPUT_MODE=auto -> auto-detects Ollama limitations
```

For models without tool support (e.g., gemma3):
```env
LOCATOR_AGENT_PROVIDER="ollama"
LOCATOR_AGENT_MODEL="gemma3:12b"
BASE_URL=http://localhost:11434/v1
STRICT_TOOL_DEFINITIONS=false
OUTPUT_MODE=prompted
```

### 11.6 For vLLM Users

```env
LOCATOR_AGENT_PROVIDER="openai"
LOCATOR_AGENT_MODEL="meta-llama/Llama-3-8B"
BASE_URL=http://vllm-server:8000/v1
STRICT_TOOL_DEFINITIONS=false
OPENAI_API_KEY=dummy
```

**Important limitation:** Setting `LOCATOR_AGENT_PROVIDER="openai"` means the vLLM-specific
`prepare_tools` hook does **not** activate. The hook (which strips `strict` and
`additionalProperties` from tool schemas) only runs when the provider is explicitly set
to `"vllm"`. Currently, no `vllm` builder entry point exists.

**Guidance for users who need schema sanitization:**
- **Recommended workaround:** Set `OUTPUT_MODE=prompted` to bypass tool schemas entirely.
  This works reliably with all vLLM-served models.
- **Future path:** Once a `vllm` builder entry point is added, users should set
  `LOCATOR_AGENT_PROVIDER="vllm"` to enable the full prepare_tools sanitization pipeline.

### 11.7 OUTPUT_MODE Decision Tree

Use this table to select the right `OUTPUT_MODE` for your provider/model combination:

| Provider | Model Supports Tools? | Model Supports `response_format`? | Recommended OUTPUT_MODE | Notes |
|---|---|---|---|---|
| `openai` | Yes | Yes | `auto` (default) | Resolves to NativeOutput. No changes needed. |
| `azure` | Yes | Yes | `auto` (default) | Resolves to NativeOutput. Same as OpenAI. |
| `openrouter` | Yes | Varies | `auto` (default) | Resolves to ToolOutput. OpenRouterProvider handles schema differences. |
| `openrouter` | No (e.g., minimax) | No | `prompted` | Model cannot use tools; PromptedOutput extracts JSON from text. |
| `ollama` | Yes (e.g., qwen3) | No | `auto` or `tool` | Auto resolves to ToolOutput. prepare_tools hook sanitizes schemas. |
| `ollama` | No (e.g., gemma3) | No | `prompted` | **Must** set explicitly. Auto mode with non-tool models will fail or produce garbage. |
| `litellm` | Depends on backend | Depends on backend | `auto` or `prompted` | Match the setting to the underlying model's capabilities. |
| `vllm` (via openai) | Yes | No | `prompted` | Workaround for missing vllm prepare_tools hook. See section 11.6. |
| Any | Unknown | Unknown | `prompted` | Safest fallback. Works with all models. Slightly lower output quality. |

---

## 12. Risk Analysis

### 12.1 Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Schema typing breaks minimax-m2.1 | Medium | Low | OpenRouterProvider handles it; document limitation |
| New Ollama builder not tested on all models | Medium | Medium | Add integration tests; fallback to prompted output |
| `output_strategy.py` logic incorrect for edge cases | Low | High | Comprehensive unit tests; manual override via `OUTPUT_MODE` |
| Programmatic Hand-Off loses LLM reasoning | Low | Low | Current orchestrator routing is deterministic (`is_failed_locator_error()`); LLM adds no decision value. Future LLM orchestration path documented in section 7.5 |
| LiteLLM double-path fix breaks existing users | Low | High | Test with actual LiteLLM proxy; document change in migration guide (section 11.4) |
| `OpenRouterProvider` API changes | Low | Medium | Pin pydantic-ai version; test in CI |
| vLLM prepare_tools hook gap | Medium | Medium | When `LOCATOR_AGENT_PROVIDER="openai"` is used for vLLM, the vLLM-specific schema sanitization hook does not activate. Users experience tool schema errors with strict-incompatible models. Mitigation: document `OUTPUT_MODE=prompted` workaround (section 11.6); plan `vllm` builder entry point in future release |
| Ollama auto-detection limitation | Medium | Medium | Auto mode cannot detect at runtime whether a specific Ollama model supports tool calling. A user who sets `OUTPUT_MODE=auto` with a non-tool-capable model (e.g., gemma3) will get failures. Mitigation: document in migration guide (section 11.5); emit a clear error message suggesting `OUTPUT_MODE=prompted` when tool call fails on Ollama |

### 12.2 Rollback Strategy

All changes are backward-compatible. If issues arise:
1. Set `OUTPUT_MODE=tool` and `STRICT_TOOL_DEFINITIONS=true` to restore exact pre-change locator agent behavior
2. Set `LOCATOR_AGENT_PROVIDER=openai` to bypass new builders for locator agents
3. Orchestrator Programmatic Hand-Off has no rollback needed -- it removes LLM dependency, making it strictly simpler. The deprecated `ORCHESTRATOR_AGENT_PROVIDER`/`ORCHESTRATOR_AGENT_MODEL` config fields are preserved but ignored
4. Revert to previous code -- no database migrations or data changes involved

### 12.3 What This ADR Does NOT Address

- **Streaming mode compatibility** (`agent.run_stream()`): Not currently used by the project.
  If added later, will need separate ADR for `ignore_streamed_leading_whitespace` and
  thinking tag handling. The `partial_output` guard in output validators (section 5.5.9)
  is forward-compatible but untested with streaming.
- **Bedrock/Gemini native providers**: Would require new builder implementations. The
  `openai` builder with `BASE_URL` + `STRICT_TOOL_DEFINITIONS=false` can serve as a
  basic workaround.
- **Model-level capability probing**: Auto-detecting whether a specific model supports
  tools at runtime. The current design relies on provider-level defaults and user config.
- **Multi-model routing**: Using different models for different agents (e.g., OpenAI for
  orchestrator, Ollama for locator). Already supported by separate `*_PROVIDER` and
  `*_MODEL` config fields.
- **StructuredDict for runtime schemas**: Evaluated in section 5.5.7. Deferred because
  the `LocatorHealingResponse` schema is stable. Could be revisited if users need custom
  response schemas via configuration.
- **Union output types** (`ModelA | ModelB`): Evaluated in sections 5.5.5 and 7.5.2. Not needed
  currently because the orchestrator uses Programmatic Hand-Off (no LLM). Documented as a
  future pattern in section 7.5.2 for when multi-agent routing requires LLM classification.
- **PromptedOutput template customization via environment variable**: Evaluated in section
  5.5.3. Deferred to avoid premature configuration complexity. The hardcoded template
  is domain-specific and sufficient for initial release.
- **NativeOutput for OpenRouter**: NativeOutput relies on `response_format: json_schema`,
  which OpenRouter does not uniformly support across all routed models. If OpenRouter
  adds native structured output support, NativeOutput could be added as an option.

---

## Summary of All File Changes (Revised -- Programmatic Hand-Off)

| # | File | Action | Phase |
|---|------|--------|-------|
| 1 | `utils/cfg.py` | MODIFY: add 2 new fields (`strict_tool_definitions`, `output_mode` with 5 values); deprecate 3 orchestrator fields (keep for backward compat) | 1 |
| 2 | `llm/providers/openai_builder.py` | MODIFY: profile + OpenAIChatModel | 1 |
| 3 | `llm/providers/azure_builder.py` | MODIFY: OpenAIChatModel | 1 |
| 4 | `llm/providers/litellm_builder.py` | MODIFY: fix bug + profile + OpenAIChatModel | 1 |
| 5 | `llm/providers/openrouter_builder.py` | CREATE: new builder | 1 |
| 6 | `llm/providers/ollama_builder.py` | CREATE: new builder | 1 |
| 7 | `llm/model_factory.py` | MODIFY: type hint | 1 |
| 8 | `llm/client_model.py` | MODIFY: type hint | 1 |
| 9 | `pyproject.toml` | MODIFY: 2 new entry points | 1 |
| 10 | `llm/output_strategy.py` | CREATE: tri-modal output selection for locator agents, prepare_tools hooks, PromptedOutput template, `_inline_refs` + `_simplify_array_items` sanitization (no orchestrator mode resolver needed) | 2 |
| 11 | `agents/locator_agent/base_locator_agent.py` | MODIFY: integrate `resolve_structured_output_type()` + `make_prepare_tools_hook()`; change `heal_async()` to accept `PromptPayload` directly + `RunUsage` + `UsageLimits`; add `_make_run_context` bridge | 2 |
| 12 | `agents/orchestrator_agent/orchestrator_agent.py` | REFACTOR: Replace LLM-based Agent with Programmatic Hand-Off. Remove model/agent creation, keep deterministic routing via `is_failed_locator_error()`, add `RunUsage` tracking | 2 |
| 13 | `kickoff_multi_agent_system.py` | MODIFY: narrow return type to `LocatorHealingResponse | NoHealingNeededResponse` | 2 |
| 14 | `schemas/api/locator_healing.py` | MODIFY: type list fields | 3 |
| 15 | `tests/unit/llm/providers/test_*_builder.py` | CREATE: builder unit tests (including Azure) | 4 |
| 16 | `tests/unit/llm/test_output_strategy.py` | CREATE: output strategy + prepare_tools tests | 4 |
| 17 | `tests/unit/agents/test_orchestrator_agent.py` | CREATE: Programmatic Hand-Off orchestrator tests (no LLM mocking needed) | 4 |
| 18 | `tests/unit/schemas/test_locator_healing.py` | CREATE: schema tests | 4 |
| 19 | `tests/integration/test_openrouter_integration.py` | CREATE: OpenRouter e2e | 4 |
| 20 | `tests/integration/test_ollama_integration.py` | CREATE: Ollama e2e | 4 |
| 21 | `tests/integration/test_backward_compat.py` | CREATE: backward compat | 4 |
| 22 | `tests/unit/llm/test_tool_schema_sanitize.py` | CREATE: unit tests for `_inline_refs`, `_simplify_array_items` | 4 |

**Total: 8 modified files, 14 new files (2 source + 12 test)**

---

## 13. ADR-001f: Advanced Tool Features and Provider Abstraction Impact

### 13.1 Context

pydantic-ai exposes several tool-level features beyond `prepare_tools` (already addressed
in section 5.5.8) that affect the Provider Abstraction Layer and Output Strategy. This
addendum evaluates four additional features and designs their integration. It also
deepens the `prepare_tools` design with advanced schema sanitization for Ollama.

**Features evaluated:**

| # | Feature | pydantic-ai API | Relevance |
|---|---------|-----------------|-----------|
| 1 | `prepare_tools` deep sanitization | `Agent(prepare_tools=fn)` | Extends section 5.5.8 with `$ref` inlining and array simplification |
| 2 | Per-tool `prepare` | `@agent.tool(prepare=fn)` | Per-tool filtering/mutation |
| 3 | `Tool.from_schema()` | `Tool.from_schema(name, schema, fn)` | Explicit JSON schema, bypass Pydantic generation |
| 4 | `ToolReturn` | `return ToolReturn(value, content, metadata)` | Rich tool return with model content + internal metadata |
| 5 | `tool_timeout` | `Agent(tool_timeout=N)` / `@agent.tool(timeout=N)` | Agent-level and per-tool timeout |

### 13.2 ModelProfile vs prepare_tools: Layered Schema Sanitization

#### 13.2.1 Layer Relationship

Section 5.5.8 introduced `make_prepare_tools_hook()` for stripping `strict` and
`additionalProperties` fields. This section clarifies how `prepare_tools` relates to
`ModelProfile` and why both are needed.

The two mechanisms operate at different layers:

```
Pydantic Schema Generation (from BaseModel class)
        |
        v
ModelProfile (strict: true/false)       <-- Layer 1: builder-level
        |                                    Controls the 'strict' flag on the
        |                                    function-call envelope. Set by
        |                                    OpenAIModelProfile in each builder.
        v
prepare_tools (schema mutations)        <-- Layer 2: agent-level
        |                                    Mutates parameters_json_schema dict.
        |                                    Cannot control the 'strict' flag.
        v
API Request to provider
```

**Key insight:** The `strict` flag in the OpenAI function-calling protocol lives
*outside* `parameters_json_schema`. It is set by pydantic-ai based on
`ModelProfile.openai_supports_strict_tool_definition`. The `prepare_tools` callback
receives `ToolDefinition` objects whose `parameters_json_schema` is a mutable dict,
but the `strict` flag is controlled by the profile, not exposed for mutation.

Therefore:
- **ModelProfile is the sole mechanism for controlling `strict: true`.** This is already
  correctly designed in section 4 (builders set profiles).
- **`prepare_tools` handles everything else:** nested `additionalProperties`, `$ref`
  inlining, array item simplification, tool filtering.

#### 13.2.2 When prepare_tools Adds Value Beyond ModelProfile

| Scenario | ModelProfile Handles? | prepare_tools Needed? |
|---|---|---|
| Remove `strict: true` flag | Yes | No |
| Remove top-level `additionalProperties` | Yes (side effect of strict=false) | No (but harmless as defense-in-depth) |
| Remove nested `additionalProperties` in `$defs` | Partially | **Yes** -- for deep nesting |
| Inline `$ref` / `$defs` for Ollama | No | **Yes** |
| Simplify array items for weak models | No | **Yes** |
| Filter out tools model cannot handle | No | **Yes** (return empty list) |

### 13.3 Enhanced prepare_tools for Ollama: Deep Schema Sanitization

#### 13.3.1 Problem

The current `_prepare_tools_ollama` (section 5.5.8) strips `strict` and
`additionalProperties` recursively. This is necessary but not sufficient for all Ollama
models.

When section 8 types `LocatorHealingResponse.metadata` as `list[dict]`, the Pydantic
schema generator produces:

```json
{
  "properties": {
    "suggestions": {"type": "array", "items": {"type": "string"}},
    "metadata": {"type": "array", "items": {"type": "object"}}
  }
}
```

Some Ollama models (particularly smaller ones) struggle with `{"type": "object"}`
array items because they do not know what properties to populate. They produce
malformed JSON like `"metadata": [{}]` or `"metadata": "none"`.

Additionally, if future schema changes introduce nested Pydantic models, the schema
generator produces `$defs` and `$ref` entries:

```json
{
  "$defs": {"InnerModel": {"type": "object", "properties": {...}}},
  "properties": {
    "field": {"$ref": "#/$defs/InnerModel"}
  }
}
```

Ollama models typically cannot resolve `$ref` references.

#### 13.3.2 Extended Sanitization Functions

Add these utility functions to `output_strategy.py` (or a dedicated
`llm/tool_schema_sanitize.py` if the module grows too large):

```python
def _inline_refs(schema: dict) -> None:
    """Replace $ref references with inlined definitions.

    Ollama models cannot resolve JSON Schema $ref. This function
    removes the $defs block and replaces all $ref pointers with
    the actual definition content.

    Mutates the schema in place. Handles single-level $defs only.

    Args:
        schema: JSON schema dict to transform.
    """
    defs = schema.pop("$defs", None)
    if not defs:
        return
    _resolve_refs_recursive(schema, defs)


def _resolve_refs_recursive(node: dict, defs: dict) -> None:
    """Walk a schema dict and replace {"$ref": "#/$defs/Foo"} with
    the definition from defs.

    Args:
        node: Current schema node to process.
        defs: The $defs mapping from the root schema.
    """
    for key, value in list(node.items()):
        if isinstance(value, dict):
            ref = value.get("$ref")
            if ref and ref.startswith("#/$defs/"):
                def_name = ref.split("/")[-1]
                if def_name in defs:
                    node[key] = dict(defs[def_name])
                    _resolve_refs_recursive(node[key], defs)
            else:
                _resolve_refs_recursive(value, defs)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    ref = item.get("$ref")
                    if ref and ref.startswith("#/$defs/"):
                        def_name = ref.split("/")[-1]
                        if def_name in defs:
                            value[i] = dict(defs[def_name])
                            _resolve_refs_recursive(value[i], defs)
                    else:
                        _resolve_refs_recursive(item, defs)


def _simplify_array_items(schema: dict) -> None:
    """Downgrade complex array item schemas to string type.

    Some Ollama models cannot produce well-formed JSON for array items
    with type: object. This function replaces complex items schemas
    with {type: string}, so the model returns stringified values that
    can be parsed downstream.

    Only applied within top-level properties (not recursively), to limit
    the scope of lossy transformation.

    Args:
        schema: JSON schema dict to simplify.
    """
    props = schema.get("properties", {})
    for prop_schema in props.values():
        if prop_schema.get("type") == "array":
            items = prop_schema.get("items", {})
            if items.get("type") == "object" and items.get("properties"):
                prop_schema["items"] = {"type": "string"}
```

#### 13.3.3 Updated _prepare_tools_ollama

```python
async def _prepare_tools_ollama(
    tools: list[ToolDefinition],
    ctx: Any,
) -> list[ToolDefinition]:
    """Strip strict-mode artifacts and simplify schemas for Ollama.

    Three-stage sanitization:
    1. Remove strict/additionalProperties (existing, section 5.5.8)
    2. Inline $ref/$defs (new -- Ollama cannot resolve references)
    3. Simplify complex array items (new -- weak models need simple types)

    Args:
        tools: List of tool definitions to modify.
        ctx: The run context (unused but required by signature).

    Returns:
        Modified tool definitions with Ollama-compatible schemas.
    """
    for tool in tools:
        _strip_strict_from_schema(tool.parameters_json_schema)
        _inline_refs(tool.parameters_json_schema)
        _simplify_array_items(tool.parameters_json_schema)
    return tools
```

#### 13.3.4 Impact on Schema Correctness

The `_simplify_array_items` transformation is **lossy**: it changes `list[dict]` items
to `list[str]` in the tool schema. This has two implications:

1. **For ToolOutput (structured output):** The model sees `items: {type: string}` and
   returns string elements. pydantic-ai's `ToolOutput` will attempt to validate against
   the original Pydantic model (`list[dict]`), which may fail. However, Ollama models
   that need this simplification should be using `PromptedOutput` (which bypasses tool
   schemas entirely). The simplification is **defense-in-depth** for edge cases.

2. **For the `_get_healed_locators` function tool:** The pre-refactoring architecture
   used this tool in the OrchestratorAgent. With Programmatic Hand-Off, this tool no
   longer exists. The schema simplification would have had no effect on parameterless
   tools regardless.

### 13.4 Per-Tool `prepare` -- Evaluation

#### 13.4.1 Feature Description

Each tool registered on an agent can have its own `prepare` function:

```python
async def my_tool_prepare(
    ctx: RunContext[PromptPayload],
    tool_def: ToolDefinition,
) -> ToolDefinition | None:
    if some_condition(ctx.deps):
        return None  # Exclude this tool for this step
    return tool_def

@agent.tool(prepare=my_tool_prepare)
def my_tool(ctx: RunContext, arg: str) -> str:
    ...
```

The per-tool `prepare` runs before the agent-wide `prepare_tools`, giving individual
tools the ability to exclude themselves or modify their own schema.

#### 13.4.2 Assessment for This Project

**Decision: Do not adopt.** Not needed in the current architecture.

Rationale:
- With Programmatic Hand-Off, the orchestrator has no Agent or tools. The locator
  agents use `output_type` (not explicit tool registration).
- The agent-wide `prepare_tools` (via `make_prepare_tools_hook`) already handles all
  schema sanitization. There is no scenario where one tool needs different treatment
  than another, because there are no explicitly registered tools in the current design.
- Per-tool `prepare` is valuable in multi-tool agents where different tools have
  different compatibility profiles. The project does not have this pattern.

**Future applicability:** If locator agents gain additional tools (e.g., a
`page_analysis` tool or a `test_generation` tool), per-tool `prepare` would allow:
- Hiding complex tools from weak models while keeping simple tools available
- Customizing schema complexity per tool based on `ctx.deps` (e.g., the provider
  serving this request)

Document as an available mechanism for future multi-tool agent designs.

### 13.5 `Tool.from_schema()` -- Evaluation

#### 13.5.1 Feature Description

`Tool.from_schema()` defines a tool with an explicit JSON schema, bypassing Pydantic's
automatic schema generation:

```python
from pydantic_ai.tools import Tool

heal_tool = Tool.from_schema(
    name="get_healed_locators",
    description="Get healed locator suggestions for a broken locator.",
    parameters_json_schema={
        "type": "object",
        "properties": {},
        "required": [],
    },
    function=_get_healed_locators_handler,
)
```

#### 13.5.2 Assessment for This Project

**Decision: Do not adopt.** Not needed; `prepare_tools` is the better mechanism.

Rationale:
- With Programmatic Hand-Off, the orchestrator has no tools. The locator agents use
  `output_type=LocatorHealingResponse`, not explicit tool registration.
- For `LocatorHealingResponse` (used as `output_type`, not as a tool), the schema
  is generated from the Pydantic model and stays in sync automatically.
  `Tool.from_schema()` would decouple the schema from the model class, creating
  schema drift risk.
- `prepare_tools` is the correct place for schema mutations because it operates on
  the generated schema dynamically. `Tool.from_schema()` is a static alternative
  that would require manual updates when the schema changes.

**Where it could help (documented for future reference):**
- If a provider needs a radically different schema that cannot be derived from the
  Pydantic model via `prepare_tools` mutations (e.g., a completely different parameter
  structure for a specific model).
- If defining tools dynamically at runtime from external configuration.

Neither scenario applies to this project.

### 13.6 `ToolReturn` -- Evaluation

#### 13.6.1 Feature Description

`ToolReturn` allows a tool to return structured data with three channels:

```python
from pydantic_ai.tools import ToolReturn
from pydantic_ai.messages import TextPart

return ToolReturn(
    return_value={"status": "ok"},              # Sent to model as tool result
    content=[TextPart("Additional context")],   # Also sent to model as extra parts
    metadata={"internal_data": "not for LLM"},  # NOT sent to model; internal only
)
```

With Programmatic Hand-Off, the orchestrator does not use tools. This evaluation is
preserved for reference in case tools are reintroduced in future agent designs.

#### 13.6.2 Use Case Analysis

**Use case 1: Healing metadata for a future tool-based orchestrator.**

```python
async def _get_healed_locators(self, ctx: RunContext[PromptPayload]) -> ToolReturn:
    result = await self._locator_agent.heal_async(ctx)
    return ToolReturn(
        return_value=result.model_dump_json(),
        metadata={
            "provider": self._cfg.locator_agent_provider,
            "model": self._cfg.locator_agent_model,
            "suggestion_count": len(result.suggestions),
        },
    )
```

Assessment: **Low priority.** With Programmatic Hand-Off, this pattern is not applicable.
If LLM-based orchestration is reintroduced (section 7.5), this could provide structured
observability.

**Use case 2: Observability for multi-provider debugging.**

```python
return ToolReturn(
    return_value=result_json,
    metadata={
        "output_mode_used": "tool",
        "retry_count": retry_count,
        "schema_sanitized": True,
    },
)
```

Assessment: **Moderate value** for debugging. However, the project's `@log` decorator
already captures function arguments and return values. pydantic-ai's `result.usage()`
provides token counts. Adding `ToolReturn.metadata` would provide more structured
observability but duplicates existing mechanisms.

**Use case 3: Additional context for model via `content`.**

```python
return ToolReturn(
    return_value=result_json,
    content=[TextPart(
        f"Found {len(result.suggestions)} suggestions. "
        f"The first suggestion uses {'CSS' if ':' not in result.suggestions[0] else 'XPath'} selector."
    )],
)
```

Assessment: **Not recommended.** Adding `content` parts risks confusing the model with
redundant information and increases token usage.

#### 13.6.3 Decision

**Do not adopt `ToolReturn` in the initial implementation.**

The current architecture uses Programmatic Hand-Off (no tools in the orchestrator).
The value proposition does not justify the added complexity and the coupling to
pydantic-ai's `ToolReturn` API.

Revisit if:
- LLM-based orchestration is reintroduced (section 7.5) with tools that need structured
  metadata.
- Multi-provider debugging in production requires structured metadata that `@log` and
  `result.usage()` cannot capture.

### 13.7 `tool_timeout` Design

#### 13.7.1 Feature Description

pydantic-ai supports timeout control at two levels:

```python
# Agent-level default (applies to all registered tools)
Agent(model, tool_timeout=30)

# Per-tool override
@agent.tool_plain(timeout=5)
def fast_tool(...): ...
```

When a tool exceeds its timeout, pydantic-ai raises a timeout error that the agent
can handle via retry logic.

#### 13.7.2 Assessment

**Decision: DEFERRED.**

`tool_timeout` is deferred. With Programmatic Hand-Off, the orchestrator has no tools.
The locator agents use `output_type` (pydantic-ai's internal ToolOutput mechanism),
which is not subject to `tool_timeout`. Timeout for locator agents is controlled by
the HTTP client timeout and `UsageLimits.request_limit`.

If LLM-based orchestration is reintroduced (section 7.5), provider-specific timeouts
should be considered. The provider-specific latency expectations are documented below
for future reference:

| Provider | Typical Latency (p95) per LLM call | Nested Tool Total (p95) | Suggested `tool_timeout` |
|---|---|---|---|
| OpenAI (gpt-4o-mini) | 2-5s | 5-12s | 30s |
| Azure (gpt-4o-mini) | 2-5s | 5-12s | 30s |
| OpenRouter (varies) | 5-15s | 12-35s | 60s |
| Ollama (local, qwen3) | 10-60s | 25-120s+ | 120s |
| vLLM (GPU server) | 3-10s | 8-25s | 60s |
| LiteLLM (proxy) | 5-20s | 12-45s | 60s |

Note: Ollama on consumer hardware (e.g., Mac M1 with 12b model) can take 30-60s
per LLM call. Nested tool calls (two LLM round trips + retries) can exceed 2 minutes.

### 13.8 Impact on Provider Builders

#### 13.8.1 Should Builders Return a `prepare_tools` Function?

**Decision: No.** Builders continue to return only the model object.

This question arises because `prepare_tools` is provider-specific and builders are
the provider-specific code. However:

1. **`prepare_tools` is an Agent-level parameter**, not a model-level parameter. The
   same model object can be shared across multiple agents with different tool
   configurations. Coupling `prepare_tools` to the model object would violate this
   separation.

2. **The builder return type is `Callable[[str, Cfg], OpenAIChatModel]`**, enforced
   by the entry_point interface in `pyproject.toml`. Returning a tuple
   `(OpenAIChatModel, prepare_tools_fn | None)` would break this contract and require
   updating `ModelFactory`, `client_model.py`, and all call sites.

3. **`make_prepare_tools_hook(provider, cfg)` already provides the correct separation.**
   The provider name is available at every agent construction site. The factory function
   selects the right callback without touching the builder interface.

```python
# Builder interface (UNCHANGED)
def ollama_builder(model_name: str, cfg: Cfg) -> OpenAIChatModel:
    ...

# prepare_tools resolved at agent construction (UNCHANGED from section 5.5.8)
prepare_tools_hook = make_prepare_tools_hook(cfg.locator_agent_provider, cfg)
agent = Agent(model=model, prepare_tools=prepare_tools_hook, ...)
```

#### 13.8.2 Entry Point Pattern (UNCHANGED)

No new entry points are needed. The provider name (already known at agent construction
time via `cfg.locator_agent_provider`) is sufficient to select both the builder (via
entry_points) and the prepare_tools hook (via `make_prepare_tools_hook()`).
Note: `cfg.orchestrator_agent_provider` is deprecated per section 7 (Programmatic Hand-Off).

### 13.9 Updated Bounded Context Map

The advanced tool features introduce refinements within the existing Output Strategy
Context:

```
┌──────────────┐    ┌─────────────────────────────┐    ┌──────────────────┐
│   Provider    │    │      Output Strategy         │    │  Agent           │
│   Context     │───>│      Context                │<───│  Orchestration   │
│              │    │                             │    │  Context         │
│ - builders   │    │ - output mode selection     │    │                  │
│ - profiles   │    │ - PromptedOutput template   │    │ - locator agent  │
│ (Layer 1)    │    │ - prepare_tools hooks       │    │ - Programmatic   │
│              │    │   (Layer 2)                 │    │   Hand-Off       │
│              │    │   - strict stripping        │    │                  │
│              │    │   - $ref inlining      NEW  │    │                  │
│              │    │   - array simplification NEW │    │                  │
│              │    │                             │    │                  │
└──────┬───────┘    └──────┬──────────────────────┘    └──────────────────┘
       │                   │
┌──────┴───────┐    ┌──────┴───────┐
│ Configuration │    │   Schema     │
│ Context      │    │   Context    │
│              │    │              │
└──────────────┘    └──────────────┘
```

The `$ref` inlining and array simplification functions are placed inside the Output
Strategy Context (within `output_strategy.py` or a companion module) because they
are schema transformations driven by provider capabilities. They do not warrant a
separate bounded context.

Note: `tool_timeout` is DEFERRED and does not appear in the context map. The
"orchestrator mode resolver" has been removed -- the orchestrator uses Programmatic
Hand-Off and does not participate in output mode resolution.

### 13.10 Updated File Changes

Changes introduced by this addendum (incremental to the Summary table):

| # | File | Action | Phase |
|---|------|--------|-------|
| -- | `llm/output_strategy.py` | MODIFY: add `_inline_refs`, `_resolve_refs_recursive`, `_simplify_array_items`; update `_prepare_tools_ollama` to call them | 2 |
| -- | `agents/orchestrator_agent/orchestrator_agent.py` | REFACTOR: Programmatic Hand-Off per section 7 (no Agent, no tool_timeout) | 2 |
| 22 | `tests/unit/llm/test_tool_schema_sanitize.py` | CREATE: unit tests for `_inline_refs`, `_simplify_array_items` | 4 |

**Updated total: 8 modified files, 14 new files (2 source + 12 test)**

### 13.11 Testing Strategy for New Features

#### 13.11.1 Schema Sanitization Tests

Location: `tests/unit/llm/test_tool_schema_sanitize.py`

```python
# --- _inline_refs tests ---

def test_inline_refs_replaces_ref_with_definition():
    """$ref pointers replaced with inlined definition content."""

def test_inline_refs_removes_defs_block():
    """$defs key removed after inlining."""

def test_inline_refs_handles_nested_refs():
    """Nested $ref chains resolved correctly."""

def test_inline_refs_no_op_without_defs():
    """Schema without $defs passes through unchanged."""

def test_inline_refs_handles_array_item_refs():
    """$ref inside array items inlined correctly."""

# --- _simplify_array_items tests ---

def test_simplify_array_items_replaces_object_items():
    """Array items with type:object + properties simplified to type:string."""

def test_simplify_array_items_preserves_string_items():
    """Array items already type:string not modified."""

def test_simplify_array_items_preserves_non_array_properties():
    """Non-array properties not affected."""

def test_simplify_array_items_ignores_object_items_without_properties():
    """Items with type:object but no properties key not simplified."""

# --- Integration: full _prepare_tools_ollama pipeline ---

async def test_ollama_prepare_tools_full_pipeline():
    """Full Ollama pipeline: strip strict + inline refs + simplify arrays."""

async def test_ollama_prepare_tools_with_locator_healing_response_schema():
    """Run Ollama sanitizer on actual LocatorHealingResponse-generated schema."""
```

#### 13.11.2 Tool Timeout Tests (Deferred -- Programmatic Hand-Off)

> **Note:** With Programmatic Hand-Off, the orchestrator has no Agent or tools.
> `tool_timeout` tests are deferred until LLM-based orchestration is reintroduced
> (section 7.5) or custom tools are added to locator agents.

### 13.12 Decision Summary Table

| Feature | Decision | Role in Architecture | Phase |
|---|---|---|---|
| `prepare_tools` deep sanitization | **Adopt** | `_inline_refs` + `_simplify_array_items` in Ollama hook | Phase 2 |
| Per-tool `prepare` | **Defer** | Not needed with current agent design | -- |
| `Tool.from_schema()` | **Defer** | Not needed; auto-generated schemas are sufficient | -- |
| `ToolReturn` | **Defer** | Not needed; Programmatic Hand-Off has no tools | -- |
| `tool_timeout` | **Defer** | Not needed with Programmatic Hand-Off orchestrator (no Agent/tools). Reserved for future LLM-based orchestration (section 7.5) | -- |

### 13.13 Risk Analysis Addendum

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| `_inline_refs` corrupts valid schema with circular `$ref` | Very Low | High | pydantic does not generate circular refs for flat models; add defensive cycle detection if schemas grow complex |
| `_simplify_array_items` causes validation failure for Ollama ToolOutput | Low | Low | Ollama models needing simplification should use PromptedOutput; simplification is defense-in-depth only |
| `tool_timeout` too low for Ollama nested calls | N/A (deferred) | N/A | Deferred with Programmatic Hand-Off; no tools in orchestrator |
| `prepare_tools` callback signature changes in pydantic-ai | Low | Medium | Pin version; callback is simple to update |
| `prepare_tools` overhead per agent step | Very Low | Very Low | Pure dict manipulation; sub-millisecond even for complex schemas |

### 13.14 Open Questions

1. **Should `_simplify_array_items` be conditionally applied based on `output_mode`?**
   Currently it runs unconditionally in the Ollama `prepare_tools` hook. If
   `output_mode=prompted`, tool schemas are not sent to the model at all, so the
   simplification is a no-op. If `output_mode=tool`, the simplification helps weak
   models but risks validation failures. The current design is safe because the Ollama
   hook only runs when `make_prepare_tools_hook()` returns a callback for Ollama, and
   the tool schema is only sent when ToolOutput is in use.

2. **Should deep sanitization functions live in `output_strategy.py` or a separate module?**
   `output_strategy.py` already contains `_strip_strict_from_schema` (section 5.5.8).
   Adding `_inline_refs`, `_resolve_refs_recursive`, and `_simplify_array_items` keeps
   all schema manipulation in one place. If the module exceeds ~500 lines (per project
   architecture guidelines), extract into `llm/tool_schema_sanitize.py`.

3. **Should `tool_timeout` auto-scale based on provider?**
   This question is deferred. With Programmatic Hand-Off, the orchestrator has no tools
   and `tool_timeout` is not needed. If LLM-based orchestration is reintroduced
   (section 7.5), provider-specific timeout defaults should be considered.

<!-- END_SECTION_13 -->

---

## 14. ADR-001g: Extensible Healing Type Architecture

### 14.1 Context

The self-healing system currently supports a single healing type: **locator healing**
(fixing broken CSS/XPath selectors when elements are not found). The error classification
is deterministic -- `is_failed_locator_error()` on each concrete agent checks whether
the error message matches known locator-failure patterns (see `selenium_locator_agent.py`
lines 52-68, `browser_locator_agent.py` lines 52-64).

Real-world Robot Framework test suites fail for many reasons beyond broken locators.
This section designs an extensible architecture that adds three new healing types while
preserving full backward compatibility with the existing locator healing flow:

1. **Locator Healing** (existing) -- broken selectors, element not found
2. **Wait/Timing Healing** (new) -- timeouts, elements not ready, race conditions
3. **Assertion Healing** (new) -- wrong assertions, value mismatches
4. **Mandatory Field Healing** (new) -- missing required form fields, validation errors

Each healing type requires different error classification logic, context requirements,
agent prompts, output schemas, and retry strategies. The architecture must allow adding
new healing types without modifying existing ones (Open/Closed Principle).

### 14.2 Healing Type Taxonomy

#### 14.2.1 Healing Type Definitions

| Healing Type | Description | Error Trigger | Context Needed | Retry Semantic |
|---|---|---|---|---|
| **Locator** | Fix broken element selectors | Element not found, invalid locator | DOM tree, failed locator, keyword args | Try each suggestion sequentially |
| **Timing** | Fix timeout/race conditions | Timeout waiting for element/condition | Keyword name, timeout value, page load state | Adjust wait time incrementally |
| **Assertion** | Fix wrong assertions or expected values | Assertion mismatch (expected vs actual) | Expected value, actual value, test context, user stories | Usually single-attempt (data issue) |
| **Mandatory Field** | Fill missing required form fields | Validation error, required field missing | Form HTML, validation messages, field metadata | Fill field and retry submission |

#### 14.2.2 Error Patterns Per Robot Framework Library

**SeleniumLibrary:**

| Healing Type | Error Pattern | Example Error Message |
|---|---|---|
| Locator | `"with locator" + "not found"` | `Element with locator 'css:#submit-btn' not found.` |
| Locator | `"No element with locator" + "found"` | `No element with locator 'id:login' found.` |
| Locator | `"Page should have contained"` | `Page should have contained element 'xpath://div[@id="main"]'.` |
| Locator | `"invalid element state"` | `InvalidElementStateException: invalid element state` |
| Timing | `"timed out after"` | `WebDriverException: timed out after 10 seconds` |
| Timing | `"timeout"` + `"waiting"` | `TimeoutException: timeout waiting for element to be visible` |
| Timing | `"Element not interactable"` | `ElementNotInteractableException: Element not interactable` |
| Assertion | `"should be"` + `!locator_context` | `Element text should be 'OK' but was 'Error'.` |
| Assertion | `"should contain"` + `!locator_context` | `Page should contain text 'Welcome' but did not.` |
| Assertion | `"should not be"` | `Checkbox should not be selected but was.` |
| Mandatory | `"required"` + `"field"` | `ValidationError: required field 'email' is empty` |
| Mandatory | `"Please fill"` | `Form validation: Please fill out this field.` |

**Browser Library (Playwright-based):**

| Healing Type | Error Pattern | Example Error Message |
|---|---|---|
| Locator | `"waiting for locator"` + `!"waiting for element to be"` | `Error: Timeout 10000ms exceeded. waiting for locator('#btn')` |
| Locator | `"Element is not an"` | `Element is not an <input> element.` |
| Timing | `"waiting for element to be"` | `Timeout 10000ms exceeded. waiting for element to be visible` |
| Timing | `"page.waitForSelector"` | `page.waitForSelector: Timeout 30000ms exceeded.` |
| Timing | `"Timeout"` + `"exceeded"` + `!locator_match` | `TimeoutError: Timeout 5000ms exceeded waiting for navigation` |
| Assertion | `"not equal"` | `Value 'Error' is not equal to 'OK'.` |
| Assertion | `"expected"` + `"received"` | `Expected: 'active', Received: 'inactive'` |
| Mandatory | `"required"` | `Element validation: Value is required` |

#### 14.2.3 Priority and Severity Model

| Healing Type | Default Priority | Severity | Rationale |
|---|---|---|---|
| Locator | 1 (highest) | High | Most common failure; well-understood fix; high success rate |
| Timing | 2 | Medium | Often intermittent; fix is speculative (wait longer); moderate success rate |
| Assertion | 3 | Low | May indicate real application bugs, not test fragility; LLM cannot know correct value |
| Mandatory | 4 (lowest) | Medium | Requires domain knowledge to fill fields; moderate success rate |

### 14.3 BaseHealingAgent ABC

#### 14.3.1 Design Rationale

The current `BaseLocatorAgent` (see `base_locator_agent.py` lines 27-442) serves as
both an abstract interface and a locator-specific implementation. It contains:

- **Generic agent logic:** LLM agent creation, output validation framework,
  `heal_async()` dispatch between LLM and DOM-based approaches
- **Locator-specific logic:** `_process_locator()`, `_sort_locators()`,
  `_filter_clickable_locators()`, `_is_locator_valid()`, `_is_locator_unique()`

The new `BaseHealingAgent` extracts the generic parts into a common ABC. The
locator-specific methods remain in `BaseLocatorAgent`, which becomes a subclass.

#### 14.3.2 BaseHealingAgent ABC

```python
# New file: agents/base_healing_agent.py

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.usage import RunUsage, UsageLimits

from SelfhealingAgents.self_healing_system.llm.client_model import get_client_model
from SelfhealingAgents.self_healing_system.llm.output_strategy import (
    make_prepare_tools_hook,
    resolve_structured_output_type,
)
from SelfhealingAgents.self_healing_system.schemas.internal_state.error_classification import (
    HealingType,
)
from SelfhealingAgents.utils.cfg import Cfg
from SelfhealingAgents.utils.logging import log


class HealingResponse(BaseModel):
    """Base response schema for all healing agents.

    All healing-type-specific responses extend this base class.
    The SelfHealingEngine and OrchestratorAgent operate on this
    base type for type-agnostic handling.

    Attributes:
        healing_type: Which healing type produced this response.
        confidence: Agent's confidence in the suggestions (0.0-1.0).
        applied_successfully: Set by the engine after attempting the fix.
    """

    healing_type: HealingType = Field(
        ..., description="The healing type that produced this response."
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Agent confidence in suggestions.",
    )
    applied_successfully: bool = Field(
        default=False,
        description="Whether the healing was applied and the keyword passed.",
    )


class BaseHealingAgent(ABC):
    """Abstract base class for all healing agents.

    Defines the contract that every healing agent must implement.
    Provides shared infrastructure for LLM agent creation, output
    strategy selection, and usage tracking. Subclasses implement
    the healing-type-specific logic.

    Attributes:
        _cfg: Application configuration.
        _usage_limits: Token and request limits.
    """

    def __init__(self, cfg: Cfg) -> None:
        """Initialize the BaseHealingAgent.

        Args:
            cfg: Application configuration.
        """
        self._cfg = cfg
        self._usage_limits: UsageLimits = UsageLimits(
            request_limit=cfg.request_limit,
            total_tokens_limit=cfg.total_tokens_limit,
        )

    @property
    @abstractmethod
    def healing_type(self) -> HealingType:
        """The healing type this agent handles.

        Returns:
            The HealingType enum value for this agent.
        """
        ...

    @abstractmethod
    @log
    async def heal_async(
        self,
        payload: "HealingPayload",
        library_type: str,
        *,
        usage: RunUsage | None = None,
        usage_limits: UsageLimits | None = None,
    ) -> HealingResponse:
        """Execute the healing logic for this agent.

        This is the main entry point called by the orchestrator after
        error classification and routing.

        Args:
            payload: Context for the healing operation.
            library_type: The RF library type ('selenium', 'browser', 'appium').
            usage: Optional shared RunUsage for cross-agent token tracking.
            usage_limits: Optional usage limits for this agent run.

        Returns:
            A HealingResponse (or subclass) with suggestions.
        """
        ...

    def _create_llm_agent(
        self,
        system_prompt: str,
        output_schema: type[BaseModel],
        deps_type: type[BaseModel] | None = None,
    ) -> Agent:
        """Create a pydantic-ai Agent with provider-aware configuration.

        Applies the output strategy (ADR-001b) and prepare_tools hooks
        (ADR-001f) to ensure compatibility across providers.

        Args:
            system_prompt: The system prompt for the agent.
            output_schema: The Pydantic model for structured output.
            deps_type: Optional Pydantic model for agent dependencies.

        Returns:
            A configured pydantic-ai Agent instance.
        """
        output_type = resolve_structured_output_type(
            output_schema,
            self._cfg,
            self._cfg.locator_agent_provider,
        )
        prepare_tools_hook = make_prepare_tools_hook(
            provider=self._cfg.locator_agent_provider,
            cfg=self._cfg,
        )
        return Agent(
            model=get_client_model(
                provider=self._cfg.locator_agent_provider,
                model=self._cfg.locator_agent_model,
                cfg=self._cfg,
            ),
            system_prompt=system_prompt,
            deps_type=deps_type,
            output_type=output_type,
            prepare_tools=prepare_tools_hook,
        )
```

### 14.4 HealingPayload (Flat Model)

The `HealingPayload` uses a flat structure where all fields are optional except for
the core required fields. This approach simplifies construction and allows context
strategies to populate only the fields relevant to each healing type.

```python
# New file: schemas/internal_state/healing_payload.py

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from SelfhealingAgents.self_healing_system.schemas.internal_state.error_classification import (
    HealingType,
)


class HealingPayload(BaseModel):
    """Unified payload for all healing operations.

    Uses a flat structure with optional fields for each healing type.
    Core fields are required; type-specific fields are optional and
    populated by context strategies based on the healing type.

    Attributes:
        error_msg: The Robot Framework error message (required).
        keyword_name: Name of the keyword that failed (required).
        keyword_args: Arguments of the keyword that failed (required).
        robot_code_line: The raw Robot keyword call that failed (required).
        file_usage_ctx: Parent test or keyword source.
        dom_tree: DOM tree at failure time.
        failed_locator: The locator that failed.
        tried_healing_memory: Previously tried suggestions.
        locator_type: Locator type restriction (css, xpath).
        healing_type_hint: Classification hint from error classifier.
        screenshot_path: Path to captured screenshot.
        screenshot_description: Text description for non-vision models.
        full_test_case: Complete test case source.
        user_stories: Related user stories for context.
        expected_value: Expected value for assertion healing.
        actual_value: Actual value for assertion healing.
        wait_settings: Current timeout configuration.
        page_load_state: Document readiness state.
        network_state: Pending XHR/fetch requests.
        element_visibility_timeline: Visibility state history.
        form_metadata: Form field definitions.
        validation_messages: Visible validation errors.
        test_data_context: Test data variables.
    """

    # --- Core fields (required) ---
    error_msg: str = Field(..., description="The Robot Framework error message.")
    keyword_name: str = Field(
        ..., description="Name of the Robot Framework keyword that failed."
    )
    keyword_args: tuple = Field(
        ..., description="Arguments of the keyword that failed."
    )
    robot_code_line: str = Field(
        ..., description="The raw Robot keyword call that failed."
    )

    # --- Common optional fields ---
    file_usage_ctx: str | None = Field(
        None, description="Parent test or keyword source of the failed call."
    )

    # --- Locator-specific fields ---
    dom_tree: str | None = Field(None, description="DOM tree at test failure.")
    failed_locator: str | None = Field(None, description="The locator that failed.")
    tried_healing_memory: list[str] = Field(
        default_factory=list,
        description="Previously tried healing suggestions.",
    )
    locator_type: str = Field(
        "css", description="Locator type restriction for suggestions."
    )

    # --- Classification hint ---
    healing_type_hint: HealingType | None = Field(
        None, description="Hint from error classifier about healing type."
    )

    # --- Screenshot context ---
    screenshot_path: str | None = Field(
        None, description="Path to screenshot captured at failure time."
    )
    screenshot_description: str | None = Field(
        None, description="LLM-generated text description of screenshot."
    )

    # --- Test case context ---
    full_test_case: str | None = Field(
        None, description="Entire test case source including setup/teardown."
    )
    user_stories: list[str] | None = Field(
        None, description="Related user stories for business context."
    )

    # --- Assertion healing context ---
    expected_value: str | None = Field(
        None, description="Expected value from the assertion."
    )
    actual_value: str | None = Field(
        None, description="Actual value from the assertion."
    )

    # --- Timing healing context ---
    wait_settings: dict[str, Any] | None = Field(
        None, description="Current timeout and wait configuration."
    )
    page_load_state: str | None = Field(
        None, description="Document readiness state at failure."
    )
    network_state: dict[str, Any] | None = Field(
        None, description="Pending network requests and timing data."
    )
    element_visibility_timeline: list[dict[str, Any]] | None = Field(
        None, description="Visibility state history of target element."
    )

    # --- Mandatory field healing context ---
    form_metadata: dict[str, Any] | None = Field(
        None, description="Form field definitions and validation state."
    )
    validation_messages: list[str] | None = Field(
        None, description="Visible validation error messages."
    )

    # --- Test data context ---
    test_data_context: dict[str, Any] | None = Field(
        None, description="Test data variables at failure time."
    )


class PromptPayload(HealingPayload):
    """Backward-compatible payload for locator healing.

    Overrides locator-specific fields to be required, preserving the
    existing PromptPayload contract. The tried_locator_memory field
    is an alias for tried_healing_memory.
    """

    dom_tree: str = Field(..., description="DOM tree at test failure.")
    failed_locator: str = Field(..., description="The locator that failed.")
    tried_locator_memory: list[str] = Field(
        default_factory=list,
        description="Previously tried locator suggestions (alias for tried_healing_memory).",
    )

    def model_post_init(self, __context: Any) -> None:
        """Synchronize tried_locator_memory with tried_healing_memory."""
        if self.tried_locator_memory and not self.tried_healing_memory:
            self.tried_healing_memory = self.tried_locator_memory
        elif self.tried_healing_memory and not self.tried_locator_memory:
            self.tried_locator_memory = self.tried_healing_memory
```

### 14.5 HealingResponse Hierarchy

```python
# Response schemas for each healing type

from pydantic import BaseModel, Field

from SelfhealingAgents.self_healing_system.agents.base_healing_agent import (
    HealingResponse,
)
from SelfhealingAgents.self_healing_system.schemas.internal_state.error_classification import (
    HealingType,
)


# --- Locator Healing Response (existing, refactored) ---

class LocatorHealingResponse(HealingResponse):
    """Response schema for locator healing results.

    Attributes:
        suggestions: Locator strings to try.
        metadata: Metadata about each suggestion.
    """

    healing_type: HealingType = HealingType.LOCATOR
    suggestions: list[str] = Field(
        ..., description="Locator suggestions for fixing the error."
    )
    metadata: list[dict] = Field(
        default_factory=list,
        description="Metadata about each suggestion.",
    )


# --- Timing Healing Response ---

class WaitStrategy(BaseModel):
    """A single wait strategy suggestion."""

    strategy_type: str = Field(
        ..., description="Wait type: 'explicit', 'polling', 'sleep', 'page_load'."
    )
    timeout_ms: int = Field(
        ..., ge=0, le=120000, description="Suggested timeout in milliseconds."
    )
    condition: str = Field(
        default="visible",
        description="Wait condition: 'visible', 'clickable', 'present', 'enabled'.",
    )
    keyword: str = Field(..., description="RF keyword to execute for this strategy.")
    keyword_args: list[str] = Field(
        default_factory=list, description="Arguments for the wait keyword."
    )
    rationale: str = Field(default="", description="Explanation for this strategy.")


class TimingHealingResponse(HealingResponse):
    """Response schema for timing healing."""

    healing_type: HealingType = HealingType.TIMING
    suggestions: list[WaitStrategy] = Field(
        ..., description="Ordered wait strategies to try."
    )
    original_timeout_ms: int = Field(
        ..., description="The original timeout that was exceeded."
    )


# --- Assertion Healing Response ---

class AssertionHealingResponse(HealingResponse):
    """Response schema for assertion healing."""

    healing_type: HealingType = HealingType.ASSERTION
    corrected_assertion: str = Field(
        default="",
        description="Corrected assertion keyword call.",
    )
    corrected_expected_value: str = Field(
        default="",
        description="Updated expected value if test data is stale.",
    )
    is_application_bug: bool = Field(
        default=False,
        description="True if the application has a real bug (do not heal).",
    )
    rationale: str = Field(
        ..., description="Explanation of diagnosis and recommendation."
    )


# --- Mandatory Field Healing Response ---

class FieldSuggestion(BaseModel):
    """A single field value suggestion."""

    field_locator: str = Field(..., description="Locator for the form field.")
    field_name: str = Field(..., description="Human-readable field name or label.")
    suggested_value: str = Field(..., description="Value to enter into the field.")
    field_type: str = Field(default="text", description="HTML input type.")
    fill_keyword: str = Field(
        default="Input Text", description="RF keyword to fill the field."
    )
    rationale: str = Field(default="", description="Rationale for this value.")


class MandatoryFieldHealingResponse(HealingResponse):
    """Response schema for mandatory field healing."""

    healing_type: HealingType = HealingType.MANDATORY_FIELD
    suggestions: list[FieldSuggestion] = Field(
        ..., description="Fields to fill before retrying form submission."
    )
```

### 14.6 HealingAgentRegistry

The registry uses a factory-based approach with flat tuple keys and "*" as wildcard
fallback for library-agnostic agents.

```python
# New file: agents/healing_agent_registry.py

from __future__ import annotations

from typing import Callable

from SelfhealingAgents.self_healing_system.agents.base_healing_agent import (
    BaseHealingAgent,
)
from SelfhealingAgents.self_healing_system.context_retrieving.library_dom_utils.base_dom_utils import (
    BaseDomUtils,
)
from SelfhealingAgents.self_healing_system.schemas.internal_state.error_classification import (
    HealingType,
)
from SelfhealingAgents.utils.cfg import Cfg


# Factory function type: (cfg, dom_utility) -> BaseHealingAgent
AgentFactory = Callable[[Cfg, BaseDomUtils | None], BaseHealingAgent]


class HealingAgentRegistry:
    """Registry mapping (HealingType, library) to agent factories.

    Uses flat tuple keys with "*" as wildcard fallback. The get_agent()
    method first checks for an exact (type, library) match, then falls
    back to (type, "*") if available.

    Attributes:
        _registry: Internal storage mapping (HealingType, str) to factory.
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._registry: dict[tuple[HealingType, str], AgentFactory] = {}

    def register(
        self,
        healing_type: HealingType,
        library: str,
        factory: AgentFactory,
    ) -> None:
        """Register an agent factory.

        Args:
            healing_type: The healing type this factory creates agents for.
            library: Library name ('selenium', 'browser', 'appium') or '*' for all.
            factory: Callable that creates an agent instance.
        """
        self._registry[(healing_type, library)] = factory

    def get_agent(
        self,
        healing_type: HealingType,
        library: str,
        cfg: Cfg,
        dom_utility: BaseDomUtils | None = None,
    ) -> BaseHealingAgent | None:
        """Get an agent instance for the given type and library.

        Looks up by exact (type, library) first, then falls back to
        wildcard (type, "*").

        Args:
            healing_type: The classified healing type.
            library: The RF library name.
            cfg: Application configuration.
            dom_utility: Optional DOM utility (required for locator agents).

        Returns:
            An instantiated healing agent, or None if not registered.
        """
        factory = self._registry.get((healing_type, library))
        if factory is None:
            factory = self._registry.get((healing_type, "*"))
        if factory is None:
            return None
        return factory(cfg, dom_utility)

    @property
    def registered_types(self) -> list[HealingType]:
        """List all healing types with at least one registered factory."""
        return sorted(
            set(ht for ht, _ in self._registry.keys()),
            key=lambda t: t.value,
        )


def create_default_registry() -> HealingAgentRegistry:
    """Create a registry with default agent registrations.

    Registers existing locator agents (Selenium, Browser) and provides
    the single source of truth for agent registration.

    Returns:
        A pre-populated HealingAgentRegistry.
    """
    from SelfhealingAgents.self_healing_system.agents.locator_agent.selenium_locator_agent import (
        SeleniumLocatorAgent,
    )
    from SelfhealingAgents.self_healing_system.agents.locator_agent.browser_locator_agent import (
        BrowserLocatorAgent,
    )

    registry = HealingAgentRegistry()

    registry.register(
        HealingType.LOCATOR,
        "selenium",
        lambda cfg, dom: SeleniumLocatorAgent(cfg=cfg, dom_utility=dom),
    )
    registry.register(
        HealingType.LOCATOR,
        "browser",
        lambda cfg, dom: BrowserLocatorAgent(cfg=cfg, dom_utility=dom),
    )

    # Future: register timing, assertion, mandatory_field agents
    # registry.register(HealingType.TIMING, "*", lambda cfg, dom: TimingAgent(cfg))
    # registry.register(HealingType.ASSERTION, "*", lambda cfg, dom: AssertionAgent(cfg))

    return registry
```

### 14.7 Concrete Agent Designs

Concrete agents extend `BaseHealingAgent` and implement the `heal_async()` method.

#### 14.7.1 Refactored BaseLocatorAgent

```python
# Modified: agents/locator_agent/base_locator_agent.py

from abc import abstractmethod

from SelfhealingAgents.self_healing_system.agents.base_healing_agent import (
    BaseHealingAgent,
    HealingResponse,
)
from SelfhealingAgents.self_healing_system.schemas.internal_state.error_classification import (
    HealingType,
)
from SelfhealingAgents.self_healing_system.schemas.internal_state.healing_payload import (
    HealingPayload,
)


class BaseLocatorAgent(BaseHealingAgent):
    """Abstract base class for locator agents.

    Extends BaseHealingAgent with locator-specific functionality.
    All existing methods (_process_locator, _sort_locators, etc.)
    are preserved unchanged.
    """

    def __init__(self, cfg: Cfg, dom_utility: BaseDomUtils) -> None:
        """Initialize the BaseLocatorAgent.

        Args:
            cfg: Application configuration.
            dom_utility: DOM utility instance for validation.
        """
        super().__init__(cfg)
        self._dom_utility = dom_utility
        # ... existing initialization unchanged ...

    @property
    def healing_type(self) -> HealingType:
        """Returns HealingType.LOCATOR."""
        return HealingType.LOCATOR

    @staticmethod
    @abstractmethod
    def is_failed_locator_error(message: str) -> bool:
        """Check if error is due to a failed locator."""
        ...

    @abstractmethod
    def _process_locator(self, locator: str) -> str:
        """Process locator for library compatibility."""
        ...

    # heal_async() signature updated to match BaseHealingAgent contract
    # Existing _heal_with_llm() and _heal_with_dom_utils() preserved
```

#### 14.7.2 TimingAgent (Sketch)

```python
# New file: agents/timing_agent/base_timing_agent.py

class BaseTimingAgent(BaseHealingAgent):
    """Base class for timing/wait healing agents."""

    @property
    def healing_type(self) -> HealingType:
        return HealingType.TIMING

    async def heal_async(
        self,
        payload: HealingPayload,
        library_type: str,
        *,
        usage: RunUsage | None = None,
        usage_limits: UsageLimits | None = None,
    ) -> TimingHealingResponse:
        """Generate wait strategy suggestions.

        Analyzes the timeout error and suggests adjusted wait strategies
        including explicit waits, polling intervals, and page load waits.
        """
        # Implementation deferred to Phase 5
        ...
```

### 14.8 Retry Strategy

The retry strategy uses section 14's API (ABC with `has_next()`, `apply_next()`,
`is_retryable()`) with the strategy stored in `ListenerState` for easy access.

```python
# New file: retry/retry_strategy.py

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from robot import running
from robot.libraries.BuiltIn import BuiltIn

from SelfhealingAgents.self_healing_system.agents.base_healing_agent import (
    HealingResponse,
)
from SelfhealingAgents.self_healing_system.schemas.api.locator_healing import (
    LocatorHealingResponse,
)
from SelfhealingAgents.self_healing_system.schemas.api.timing_healing import (
    TimingHealingResponse,
)
from SelfhealingAgents.self_healing_system.schemas.api.assertion_healing import (
    AssertionHealingResponse,
)
from SelfhealingAgents.self_healing_system.schemas.api.mandatory_field_healing import (
    MandatoryFieldHealingResponse,
)
from SelfhealingAgents.self_healing_system.schemas.internal_state.error_classification import (
    HealingType,
)


class RetryStrategy(ABC):
    """Abstract retry strategy for a healing type.

    Each healing type has different retry semantics. The strategy
    encapsulates how to check for remaining suggestions, apply them
    to the keyword, and determine whether retrying is appropriate.
    """

    @abstractmethod
    def has_next(self, response: HealingResponse) -> bool:
        """Check if there are more suggestions to try."""
        ...

    @abstractmethod
    def apply_next(
        self,
        response: HealingResponse,
        data: running.Keyword,
    ) -> Any:
        """Pop the next suggestion and apply it to the keyword."""
        ...

    @abstractmethod
    def is_retryable(self, response: HealingResponse) -> bool:
        """Check if this healing type supports retrying."""
        ...


class LocatorRetryStrategy(RetryStrategy):
    """Retry strategy for locator healing (current behavior)."""

    def has_next(self, response: HealingResponse) -> bool:
        if not isinstance(response, LocatorHealingResponse):
            return False
        return len(response.suggestions) > 0

    def apply_next(
        self,
        response: HealingResponse,
        data: running.Keyword,
    ) -> Any:
        assert isinstance(response, LocatorHealingResponse)
        suggestion = response.suggestions.pop(0)
        data.args = list(data.args)
        data.args[0] = suggestion
        return BuiltIn().run_keyword(data.name, *data.args)

    def is_retryable(self, response: HealingResponse) -> bool:
        return True


class TimingRetryStrategy(RetryStrategy):
    """Retry strategy for timing healing."""

    def has_next(self, response: HealingResponse) -> bool:
        if not isinstance(response, TimingHealingResponse):
            return False
        return len(response.suggestions) > 0

    def apply_next(
        self,
        response: HealingResponse,
        data: running.Keyword,
    ) -> Any:
        assert isinstance(response, TimingHealingResponse)
        strategy = response.suggestions.pop(0)
        # Execute wait keyword first
        BuiltIn().run_keyword(strategy.keyword, *strategy.keyword_args)
        # Then re-run the original keyword unchanged
        return BuiltIn().run_keyword(data.name, *data.args)

    def is_retryable(self, response: HealingResponse) -> bool:
        return True


class AssertionRetryStrategy(RetryStrategy):
    """Retry strategy for assertion healing.

    Assertion healing is generally NOT retryable at runtime.
    """

    def has_next(self, response: HealingResponse) -> bool:
        return False

    def apply_next(
        self,
        response: HealingResponse,
        data: running.Keyword,
    ) -> Any:
        raise NotImplementedError("Assertion healing does not support runtime retry.")

    def is_retryable(self, response: HealingResponse) -> bool:
        if not isinstance(response, AssertionHealingResponse):
            return False
        return not response.is_application_bug


class MandatoryFieldRetryStrategy(RetryStrategy):
    """Retry strategy for mandatory field healing."""

    def has_next(self, response: HealingResponse) -> bool:
        if not isinstance(response, MandatoryFieldHealingResponse):
            return False
        return len(response.suggestions) > 0

    def apply_next(
        self,
        response: HealingResponse,
        data: running.Keyword,
    ) -> Any:
        assert isinstance(response, MandatoryFieldHealingResponse)
        # Fill ALL suggested fields before retrying submission
        while response.suggestions:
            field = response.suggestions.pop(0)
            BuiltIn().run_keyword(
                field.fill_keyword,
                field.field_locator,
                field.suggested_value,
            )
        return BuiltIn().run_keyword(data.name, *data.args)

    def is_retryable(self, response: HealingResponse) -> bool:
        return True


# Strategy map: HealingType -> strategy class (instantiated per-use)
_STRATEGY_MAP: dict[HealingType, type[RetryStrategy]] = {
    HealingType.LOCATOR: LocatorRetryStrategy,
    HealingType.TIMING: TimingRetryStrategy,
    HealingType.ASSERTION: AssertionRetryStrategy,
    HealingType.MANDATORY_FIELD: MandatoryFieldRetryStrategy,
}


def get_retry_strategy(healing_type: HealingType) -> RetryStrategy:
    """Get a retry strategy instance for a healing type."""
    strategy_cls = _STRATEGY_MAP.get(healing_type)
    if strategy_cls is None:
        raise ValueError(f"No retry strategy for {healing_type.value}")
    return strategy_cls()
```

### 14.9 File Changes

#### 14.9.1 New Files

| File | Description |
|------|-------------|
| `agents/base_healing_agent.py` | `BaseHealingAgent` ABC, `HealingResponse` base schema |
| `agents/healing_agent_registry.py` | `HealingAgentRegistry`, `create_default_registry()` |
| `schemas/internal_state/healing_payload.py` | `HealingPayload` flat schema, `PromptPayload` subclass |
| `schemas/api/timing_healing.py` | `WaitStrategy`, `TimingHealingResponse` |
| `schemas/api/assertion_healing.py` | `AssertionHealingResponse` |
| `schemas/api/mandatory_field_healing.py` | `FieldSuggestion`, `MandatoryFieldHealingResponse` |
| `retry/retry_strategy.py` | `RetryStrategy` ABC, concrete strategies |

#### 14.9.2 Modified Files

| File | Change |
|------|--------|
| `agents/locator_agent/base_locator_agent.py` | Extend `BaseHealingAgent`; implement `healing_type` property |
| `schemas/api/locator_healing.py` | `LocatorHealingResponse` extends `HealingResponse` |
| `schemas/internal_state/listener_state.py` | Add `healing_response`, `current_strategy` fields |
| `self_healing_engine.py` | Replace `_try_locator_suggestions()` with `_try_healing_suggestions()` |

---

## 15. ADR-001h: Orchestrator Hybrid Routing

### 15.1 Problem Statement

ADR-001d (Section 7) established Programmatic Hand-Off as the correct orchestration
pattern because the system had exactly one healing type (locator) and routing was
fully deterministic via `is_failed_locator_error()`. This decision remains sound for
the single-healing-type case.

With multiple healing types, some errors are **ambiguous**:

| Error Message | Possible Classification |
|---|---|
| `"Element with locator '#btn-login' not found"` | Locator (unambiguous) |
| `"Timeout 10000ms exceeded waiting for element '#btn-login'"` | Locator OR Timing |
| `"Element is not interactable"` | Locator OR Timing OR Mandatory Field |

The hybrid approach: deterministic classification for clear-cut errors (>80%),
LLM classification only for genuinely ambiguous ones (~15%).

### 15.2 Error Classification Design

#### 15.2.1 HealingType Enum

```python
# File: error_classification/healing_types.py

from enum import Enum


class HealingType(str, Enum):
    """Enumeration of supported healing types.

    Uses str mixin for natural JSON serialization and string comparison.
    UNKNOWN indicates no healing agent is applicable.
    """

    LOCATOR = "locator"
    TIMING = "timing"
    ASSERTION = "assertion"
    MANDATORY_FIELD = "mandatory_field"
    UNKNOWN = "unknown"
```

#### 15.2.2 ErrorClassification Schema

```python
# File: error_classification/error_classification.py

from pydantic import BaseModel, Field

from SelfhealingAgents.self_healing_system.error_classification.healing_types import (
    HealingType,
)


class ErrorClassification(BaseModel):
    """Result of error classification.

    Attributes:
        healing_type: The classified healing type (not 'type' for clarity).
        confidence: Classification confidence (1.0 for deterministic matches).
        tier: Classification tier (1 = deterministic, 2 = LLM).
        alternatives: Other healing types that were considered.
        reasoning: LLM explanation (empty for Tier 1).
        raw_error: The original error message.
    """

    healing_type: HealingType = Field(
        ..., description="The classified healing type."
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Classification confidence. 1.0 means deterministic match.",
    )
    tier: int = Field(
        ..., ge=1, le=2, description="Classification tier (1 or 2)."
    )
    alternatives: list[HealingType] = Field(
        default_factory=list,
        description="Other healing types that were considered.",
    )
    reasoning: str = Field(
        default="",
        description="Human-readable reasoning (populated by Tier 2 only).",
    )
    raw_error: str = Field(
        ..., description="The original error message that was classified."
    )
```

#### 15.2.3 PatternRegistry and ErrorPattern

```python
# File: error_classification/patterns.py

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from SelfhealingAgents.self_healing_system.error_classification.healing_types import (
    HealingType,
)


@dataclass(frozen=True)
class ErrorPattern:
    """A single error pattern for deterministic classification.

    Attributes:
        healing_type: The healing type this pattern maps to.
        library_type: Library this applies to ('selenium', 'browser', '*').
        pattern: Compiled regex pattern.
        description: Human-readable description.
        priority: Lower = higher priority (for ordering within same type).
        exclusive: If True, an unambiguous match prevents Tier 2.
    """

    healing_type: HealingType
    library_type: str
    pattern: re.Pattern
    description: str
    priority: int = 0
    exclusive: bool = True


class PatternRegistry:
    """Registry of error patterns for Tier 1 classification.

    Patterns are evaluated against error messages. The match() method
    returns all matching healing types, allowing detection of ambiguity.
    """

    def __init__(self) -> None:
        self._patterns: list[ErrorPattern] = []

    def register(self, pattern: ErrorPattern) -> None:
        """Register an error pattern."""
        self._patterns.append(pattern)

    def match(self, error_msg: str, library_type: str) -> list[ErrorPattern]:
        """Find all patterns that match the error message.

        Args:
            error_msg: The error message to classify.
            library_type: The library type ('selenium', 'browser').

        Returns:
            List of matching ErrorPattern objects, sorted by priority.
        """
        matches = []
        for p in self._patterns:
            if p.library_type not in (library_type, "*"):
                continue
            if p.pattern.search(error_msg):
                matches.append(p)
        return sorted(matches, key=lambda x: x.priority)

    def get_matching_types(
        self, error_msg: str, library_type: str
    ) -> list[HealingType]:
        """Get deduplicated list of matching healing types."""
        patterns = self.match(error_msg, library_type)
        seen = set()
        result = []
        for p in patterns:
            if p.healing_type not in seen:
                seen.add(p.healing_type)
                result.append(p.healing_type)
        return result
```

#### 15.2.4 Default Pattern Registration

```python
# File: error_classification/default_patterns.py

import re
from SelfhealingAgents.self_healing_system.error_classification.patterns import (
    ErrorPattern,
    PatternRegistry,
)
from SelfhealingAgents.self_healing_system.error_classification.healing_types import (
    HealingType,
)


def register_default_patterns(registry: PatternRegistry) -> None:
    """Register all default error patterns.

    These patterns are derived from existing is_failed_locator_error()
    implementations, ensuring backward compatibility.
    """
    _register_locator_patterns_selenium(registry)
    _register_locator_patterns_browser(registry)
    _register_timing_patterns(registry)
    _register_assertion_patterns(registry)
    _register_mandatory_field_patterns(registry)


def _register_locator_patterns_selenium(registry: PatternRegistry) -> None:
    """Locator patterns for SeleniumLibrary."""
    registry.register(ErrorPattern(
        healing_type=HealingType.LOCATOR,
        library_type="selenium",
        pattern=re.compile(r"with locator.*not found", re.IGNORECASE),
        description="SeleniumLibrary: element with locator not found",
        priority=10,
    ))
    registry.register(ErrorPattern(
        healing_type=HealingType.LOCATOR,
        library_type="selenium",
        pattern=re.compile(r"No element with locator.*found", re.IGNORECASE),
        description="SeleniumLibrary: no element with locator found",
        priority=10,
    ))
    registry.register(ErrorPattern(
        healing_type=HealingType.LOCATOR,
        library_type="selenium",
        pattern=re.compile(r"Page should have contained", re.IGNORECASE),
        description="SeleniumLibrary: page content check",
        priority=10,
    ))
    registry.register(ErrorPattern(
        healing_type=HealingType.LOCATOR,
        library_type="selenium",
        pattern=re.compile(r"invalid element state", re.IGNORECASE),
        description="SeleniumLibrary: invalid element state",
        priority=15,
        exclusive=False,  # Could also be timing
    ))


def _register_locator_patterns_browser(registry: PatternRegistry) -> None:
    """Locator patterns for Browser library."""
    registry.register(ErrorPattern(
        healing_type=HealingType.LOCATOR,
        library_type="browser",
        pattern=re.compile(r"waiting for locator(?!.*waiting for element to be)", re.IGNORECASE),
        description="Browser: waiting for locator (excluding timing)",
        priority=10,
    ))
    registry.register(ErrorPattern(
        healing_type=HealingType.LOCATOR,
        library_type="browser",
        pattern=re.compile(r"Element is not an", re.IGNORECASE),
        description="Browser: element is not expected type",
        priority=10,
    ))


def _register_timing_patterns(registry: PatternRegistry) -> None:
    """Timing patterns across libraries."""
    registry.register(ErrorPattern(
        healing_type=HealingType.TIMING,
        library_type="*",
        pattern=re.compile(r"[Tt]ime(?:d\s*)?out.*exceeded", re.IGNORECASE),
        description="Generic: timeout exceeded",
        priority=15,
        exclusive=False,
    ))
    registry.register(ErrorPattern(
        healing_type=HealingType.TIMING,
        library_type="browser",
        pattern=re.compile(r"waiting for element to be", re.IGNORECASE),
        description="Browser: waiting for element state",
        priority=10,
    ))
    registry.register(ErrorPattern(
        healing_type=HealingType.TIMING,
        library_type="selenium",
        pattern=re.compile(r"Element not interactable", re.IGNORECASE),
        description="SeleniumLibrary: element not interactable",
        priority=15,
        exclusive=False,
    ))


def _register_assertion_patterns(registry: PatternRegistry) -> None:
    """Assertion patterns across libraries."""
    registry.register(ErrorPattern(
        healing_type=HealingType.ASSERTION,
        library_type="*",
        pattern=re.compile(
            r"(should be|should contain|should not be)(?!.*locator)(?!.*element)",
            re.IGNORECASE,
        ),
        description="Generic: assertion keyword failure",
        priority=15,
    ))
    registry.register(ErrorPattern(
        healing_type=HealingType.ASSERTION,
        library_type="browser",
        pattern=re.compile(r"not equal", re.IGNORECASE),
        description="Browser: value not equal",
        priority=15,
    ))
    registry.register(ErrorPattern(
        healing_type=HealingType.ASSERTION,
        library_type="browser",
        pattern=re.compile(r"expected.*received", re.IGNORECASE),
        description="Browser: expected vs received mismatch",
        priority=15,
    ))


def _register_mandatory_field_patterns(registry: PatternRegistry) -> None:
    """Mandatory field patterns across libraries."""
    registry.register(ErrorPattern(
        healing_type=HealingType.MANDATORY_FIELD,
        library_type="*",
        pattern=re.compile(r"required\s+(field|attribute)", re.IGNORECASE),
        description="Generic: required field missing",
        priority=20,
    ))
    registry.register(ErrorPattern(
        healing_type=HealingType.MANDATORY_FIELD,
        library_type="*",
        pattern=re.compile(r"Please fill", re.IGNORECASE),
        description="Generic: browser validation message",
        priority=20,
    ))
```

#### 15.2.5 ErrorClassifier

```python
# File: error_classification/classifier.py

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic_ai.usage import RunUsage
from robot.api import logger as rf_logger

from SelfhealingAgents.self_healing_system.error_classification.error_classification import (
    ErrorClassification,
)
from SelfhealingAgents.self_healing_system.error_classification.healing_types import (
    HealingType,
)
from SelfhealingAgents.self_healing_system.error_classification.patterns import (
    PatternRegistry,
)

if TYPE_CHECKING:
    from SelfhealingAgents.self_healing_system.error_classification.llm_classifier import (
        LLMClassifier,
    )
    from SelfhealingAgents.self_healing_system.schemas.internal_state.healing_payload import (
        HealingPayload,
    )
    from SelfhealingAgents.utils.cfg import Cfg


class ErrorClassifier:
    """Two-tier hybrid error classifier.

    Tier 1 uses deterministic pattern matching (no LLM).
    Tier 2 uses an LLM for ambiguous errors (only when configured).
    """

    def __init__(
        self,
        registry: PatternRegistry,
        cfg: "Cfg",
        llm_classifier: "LLMClassifier | None" = None,
    ) -> None:
        self._registry = registry
        self._cfg = cfg
        self._llm_classifier = llm_classifier
        self._enabled_types = self._parse_enabled_types(cfg.healing_types_enabled)
        self._mode = cfg.error_classification_mode

    async def classify(
        self,
        error_msg: str,
        library_type: str,
        payload: "HealingPayload | None" = None,
        *,
        usage: RunUsage | None = None,
    ) -> ErrorClassification:
        """Classify an error message into a healing type.

        Args:
            error_msg: The Robot Framework error message.
            library_type: The library type ('selenium', 'browser').
            payload: Optional payload for additional Tier 2 context.
            usage: Optional shared usage tracker.

        Returns:
            ErrorClassification with determined healing type.
        """
        # Tier 1: Deterministic
        all_matches = self._registry.get_matching_types(error_msg, library_type)
        matches = [t for t in all_matches if t in self._enabled_types]

        if len(matches) == 1:
            rf_logger.debug(f"Tier 1: Unambiguous -> {matches[0].value}")
            return ErrorClassification(
                healing_type=matches[0],
                confidence=1.0,
                tier=1,
                alternatives=[],
                raw_error=error_msg,
            )

        if len(matches) == 0:
            rf_logger.debug("Tier 1: No match -> UNKNOWN")
            return ErrorClassification(
                healing_type=HealingType.UNKNOWN,
                confidence=1.0,
                tier=1,
                alternatives=[t for t in all_matches if t not in self._enabled_types],
                raw_error=error_msg,
            )

        # Ambiguous: 2+ enabled types matched
        if self._mode != "hybrid" or self._llm_classifier is None:
            rf_logger.info(f"Tier 1: Ambiguous ({[t.value for t in matches]}), defaulting to {matches[0].value}")
            return ErrorClassification(
                healing_type=matches[0],
                confidence=0.5,
                tier=1,
                alternatives=matches[1:],
                raw_error=error_msg,
            )

        # Tier 2: LLM Classification
        rf_logger.info(f"Tier 1: Ambiguous, escalating to Tier 2")
        return await self._llm_classifier.classify(
            error_msg=error_msg,
            library_type=library_type,
            candidate_types=matches,
            payload=payload,
            usage=usage,
        )

    @staticmethod
    def _parse_enabled_types(config_value: str) -> set[HealingType]:
        """Parse comma-separated healing type names."""
        result = set()
        for name in config_value.split(","):
            name = name.strip().lower()
            if name:
                try:
                    result.add(HealingType(name))
                except ValueError:
                    rf_logger.warn(f"Unknown healing type: '{name}'")
        return result
```

### 15.3 Hybrid Router Architecture

```
Error Message + Library Type
        |
        v
  +-----------------------+
  | Tier 1: Deterministic |  Pattern-matched classification
  | PatternRegistry       |  No LLM call
  +-----------+-----------+
              |
     Result?  |
              |
  +-----------+------------+-----------------+
  |                        |                 |
  UNAMBIGUOUS            AMBIGUOUS         NO MATCH
  (1 type matches)     (2+ types match)   (0 types match)
  |                        |                 |
  v                        v                 v
  Route to              +---+---+          Return
  healing agent         | Tier 2|          UNKNOWN
                        | LLM   |
                        +---+---+
                            |
                            v
                        Classification
                        -> Route to agent
```

### 15.4 Revised OrchestratorAgent

```python
# Modified: agents/orchestrator_agent/orchestrator_agent.py

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic_ai.usage import RunUsage, UsageLimits
from robot.api import logger as rf_logger

from SelfhealingAgents.self_healing_system.agents.base_healing_agent import (
    HealingResponse,
)
from SelfhealingAgents.self_healing_system.error_classification.healing_types import (
    HealingType,
)
from SelfhealingAgents.self_healing_system.schemas.api.locator_healing import (
    NoHealingNeededResponse,
)

if TYPE_CHECKING:
    from SelfhealingAgents.self_healing_system.agents.healing_agent_registry import (
        HealingAgentRegistry,
    )
    from SelfhealingAgents.self_healing_system.error_classification.classifier import (
        ErrorClassifier,
    )
    from SelfhealingAgents.self_healing_system.schemas.internal_state.healing_payload import (
        HealingPayload,
    )
    from SelfhealingAgents.utils.cfg import Cfg


_LOW_CONFIDENCE_THRESHOLD: float = 0.3


class OrchestratorAgent:
    """Routes failure payloads to the appropriate healing agent.

    Uses hybrid classification (Tier 1 deterministic, Tier 2 LLM)
    followed by registry lookup to dispatch to the correct agent.
    """

    def __init__(
        self,
        cfg: "Cfg",
        classifier: "ErrorClassifier",
        registry: "HealingAgentRegistry",
    ) -> None:
        """Initialize the OrchestratorAgent.

        Args:
            cfg: Application configuration.
            classifier: Error classifier for determining healing type.
            registry: Registry of available healing agents.
        """
        self._cfg = cfg
        self._classifier = classifier
        self._registry = registry
        self._usage_limits = UsageLimits(
            request_limit=cfg.request_limit,
            total_tokens_limit=cfg.total_tokens_limit,
        )

    async def run_async(
        self,
        robot_ctx_payload: "HealingPayload",
        library_type: str,
    ) -> HealingResponse | NoHealingNeededResponse:
        """Run classification and delegate to the appropriate agent.

        Args:
            robot_ctx_payload: Context for the healing process.
            library_type: The library type ('selenium', 'browser').

        Returns:
            A healing response or NoHealingNeededResponse.
        """
        usage = RunUsage()

        # Step 1: Classify error
        classification = await self._classifier.classify(
            error_msg=robot_ctx_payload.error_msg,
            library_type=library_type,
            payload=robot_ctx_payload,
            usage=usage,
        )

        rf_logger.info(
            f"Classified as {classification.healing_type.value} "
            f"(tier={classification.tier}, confidence={classification.confidence})",
            also_console=True,
        )

        # Step 2: Check for UNKNOWN or low confidence
        if classification.healing_type == HealingType.UNKNOWN:
            return NoHealingNeededResponse(message=robot_ctx_payload.error_msg)

        if classification.confidence < _LOW_CONFIDENCE_THRESHOLD:
            rf_logger.warn(f"Low confidence ({classification.confidence}), skipping healing")
            return NoHealingNeededResponse(message=robot_ctx_payload.error_msg)

        # Step 3: Get agent from registry
        agent = self._registry.get_agent(
            classification.healing_type,
            library_type,
            self._cfg,
            None,  # dom_utility injected separately for locator agents
        )
        if agent is None:
            rf_logger.warn(
                f"No agent for type={classification.healing_type.value}, "
                f"library={library_type}"
            )
            return NoHealingNeededResponse(message=robot_ctx_payload.error_msg)

        # Step 4: Delegate to agent
        result = await agent.heal_async(
            robot_ctx_payload,
            library_type,
            usage=usage,
            usage_limits=self._usage_limits,
        )

        rf_logger.info(
            f"Healing complete. Type={classification.healing_type.value}, "
            f"tokens={usage.total_tokens}",
            also_console=True,
        )

        return result
```

### 15.5 LLM Classification (Tier 2)

```python
# File: error_classification/llm_classifier.py

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.usage import RunUsage, UsageLimits

from SelfhealingAgents.self_healing_system.error_classification.error_classification import (
    ErrorClassification,
)
from SelfhealingAgents.self_healing_system.error_classification.healing_types import (
    HealingType,
)
from SelfhealingAgents.self_healing_system.llm.client_model import get_client_model

if TYPE_CHECKING:
    from SelfhealingAgents.self_healing_system.schemas.internal_state.healing_payload import (
        HealingPayload,
    )
    from SelfhealingAgents.utils.cfg import Cfg


# Union output types for LLM classification
class LocatorClassification(BaseModel):
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str

class TimingClassification(BaseModel):
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str

class AssertionClassification(BaseModel):
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str

class MandatoryFieldClassification(BaseModel):
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str

class UnknownClassification(BaseModel):
    reasoning: str


ClassificationOutput = (
    LocatorClassification
    | TimingClassification
    | AssertionClassification
    | MandatoryFieldClassification
    | UnknownClassification
)

_OUTPUT_TYPE_MAP: dict[type, HealingType] = {
    LocatorClassification: HealingType.LOCATOR,
    TimingClassification: HealingType.TIMING,
    AssertionClassification: HealingType.ASSERTION,
    MandatoryFieldClassification: HealingType.MANDATORY_FIELD,
    UnknownClassification: HealingType.UNKNOWN,
}


CLASSIFICATION_SYSTEM_PROMPT = """\
You are an error classifier for Robot Framework test failures.

Classify the error into exactly one category:
- LocatorClassification: Broken selector, element not found in DOM
- TimingClassification: Timeout, element exists but not ready
- AssertionClassification: Value mismatch in assertion check
- MandatoryFieldClassification: Required form field missing value
- UnknownClassification: None of the above apply

Provide confidence (0.0-1.0) and brief reasoning.\
"""


class LLMClassifier:
    """LLM-based classifier for Tier 2 ambiguous errors."""

    def __init__(self, cfg: "Cfg") -> None:
        provider = cfg.classification_provider or cfg.locator_agent_provider
        model = cfg.classification_model or cfg.locator_agent_model

        self._agent: Agent[None, ClassificationOutput] = Agent(
            model=get_client_model(provider=provider, model=model, cfg=cfg),
            system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
            output_type=ClassificationOutput,
        )
        self._usage_limits = UsageLimits(request_limit=2)

    async def classify(
        self,
        error_msg: str,
        library_type: str,
        candidate_types: list[HealingType],
        payload: "HealingPayload | None" = None,
        *,
        usage: RunUsage | None = None,
    ) -> ErrorClassification:
        """Classify an ambiguous error using the LLM."""
        prompt_parts = [
            f"Error: {error_msg}",
            f"Library: {library_type}",
            f"Candidates: {[t.value for t in candidate_types]}",
        ]
        if payload:
            prompt_parts.append(f"Keyword: {payload.keyword_name}")

        result = await self._agent.run(
            "\n".join(prompt_parts),
            usage=usage,
            usage_limits=self._usage_limits,
        )

        output = result.output
        healing_type = _OUTPUT_TYPE_MAP.get(type(output), HealingType.UNKNOWN)
        confidence = getattr(output, "confidence", 0.5)
        reasoning = getattr(output, "reasoning", "")

        return ErrorClassification(
            healing_type=healing_type,
            confidence=confidence,
            tier=2,
            alternatives=[t for t in candidate_types if t != healing_type],
            reasoning=reasoning,
            raw_error=error_msg,
        )
```

### 15.6 Configuration

```python
# Additions to utils/cfg.py

class Cfg(BaseSettings):
    # ... existing fields ...

    healing_types_enabled: str = Field(
        "locator",
        env="HEALING_TYPES_ENABLED",
        description="Comma-separated enabled healing types.",
    )

    error_classification_mode: str = Field(
        "deterministic",
        env="ERROR_CLASSIFICATION_MODE",
        description="'deterministic' (Tier 1 only) or 'hybrid' (Tier 1 + 2).",
    )

    classification_provider: str = Field(
        "",
        env="CLASSIFICATION_PROVIDER",
        description="LLM provider for Tier 2 classification.",
    )

    classification_model: str = Field(
        "",
        env="CLASSIFICATION_MODEL",
        description="Model for Tier 2 classification.",
    )
```

### 15.7 Backward Compatibility

When `HEALING_TYPES_ENABLED=locator` (default) and `ERROR_CLASSIFICATION_MODE=deterministic`
(default), the system behaves identically to the current ADR-001d implementation:

1. Errors matching locator patterns -> classified as LOCATOR -> routed to locator agent
2. Errors matching no patterns -> classified as UNKNOWN -> NoHealingNeededResponse
3. No LLM classification calls
4. All existing tests pass unchanged

### 15.8 KickoffMultiAgentSystem Changes

The `kickoff_healing()` method evolves to build the classifier and registry.

```python
# Modified: kickoff_multi_agent_system.py

from SelfhealingAgents.self_healing_system.error_classification.classifier import (
    ErrorClassifier,
)
from SelfhealingAgents.self_healing_system.error_classification.patterns import (
    PatternRegistry,
)
from SelfhealingAgents.self_healing_system.error_classification.default_patterns import (
    register_default_patterns,
)
from SelfhealingAgents.self_healing_system.agents.healing_agent_registry import (
    create_default_registry,
)


class KickoffMultiAgentSystem:

    @staticmethod
    def kickoff_healing(
        data: running.Keyword,
        result: result.Keyword,
        *,
        cfg: Cfg,
        tried_locator_memory: list[str],
    ) -> HealingResponse | NoHealingNeededResponse:
        # ... existing library detection and DOM utility creation ...

        # Build classifier
        pattern_registry = PatternRegistry()
        register_default_patterns(pattern_registry)

        llm_classifier = None
        if cfg.error_classification_mode == "hybrid":
            from SelfhealingAgents.self_healing_system.error_classification.llm_classifier import (
                LLMClassifier,
            )
            llm_classifier = LLMClassifier(cfg)

        classifier = ErrorClassifier(
            registry=pattern_registry,
            cfg=cfg,
            llm_classifier=llm_classifier,
        )

        # Build agent registry
        agent_registry = create_default_registry()

        # Build orchestrator
        orchestrator = OrchestratorAgent(
            cfg=cfg,
            classifier=classifier,
            registry=agent_registry,
        )

        # Build payload and run
        payload = RobotCtxRetriever.get_healing_payload(
            data, result, dom_utility=dom_utility
        )
        payload.tried_healing_memory = tried_locator_memory

        return asyncio.get_event_loop().run_until_complete(
            orchestrator.run_async(payload, library_type=agent_type)
        )
```

### 15.9 SelfHealingEngine Generalization

The `_try_locator_suggestions()` method is replaced with a generic
`_try_healing_suggestions()` that uses the retry strategy from ListenerState.

```python
# Modified: self_healing_engine.py

from SelfhealingAgents.self_healing_system.retry.retry_strategy import (
    get_retry_strategy,
)


class SelfHealingEngine:

    def _try_healing_suggestions(self, data: running.Keyword) -> Any:
        """Apply healing suggestions using the appropriate retry strategy."""
        response = self._listener_state.healing_response
        if response is None:
            return None

        strategy = get_retry_strategy(response.healing_type)

        if not strategy.is_retryable(response):
            rf_logger.info(
                f"Healing type '{response.healing_type.value}' "
                f"does not support retry.",
                also_console=True,
            )
            return None

        if not strategy.has_next(response):
            return None

        try:
            result = strategy.apply_next(response, data)
            self._listener_state.healed = True
            return result
        except Exception as e:
            rf_logger.debug(f"Healing suggestion failed: {e}")
            raise
```

### 15.10 File Changes

#### 15.10.1 New Files

| File | Description |
|------|-------------|
| `error_classification/__init__.py` | Package init |
| `error_classification/healing_types.py` | `HealingType` enum |
| `error_classification/error_classification.py` | `ErrorClassification` schema |
| `error_classification/patterns.py` | `ErrorPattern`, `PatternRegistry` |
| `error_classification/default_patterns.py` | Default pattern registration |
| `error_classification/classifier.py` | `ErrorClassifier` (Tier 1 + routing) |
| `error_classification/llm_classifier.py` | `LLMClassifier` (Tier 2) |

#### 15.10.2 Modified Files

| File | Change |
|------|--------|
| `agents/orchestrator_agent/orchestrator_agent.py` | Use classifier + registry |
| `kickoff_multi_agent_system.py` | Build classifier, registry, new orchestrator |
| `utils/cfg.py` | Add classification config fields |
| `self_healing_engine.py` | Generalize retry loop |
| `schemas/internal_state/listener_state.py` | Add `healing_response` field |

---

## 16. ADR-001i: Context Enrichment and DDD Expansion

### 16.1 Context

The current system is optimized for locator healing. Future healing types require
different context. This section designs:

- Context strategy pattern for type-specific gathering
- Screenshot capture integration
- User story retrieval
- Token budget management
- Extended reporting

### 16.2 Context Requirements Matrix

| Context Element | Locator | Timing | Assertion | Mandatory Field |
|---|---|---|---|---|
| `error_msg` | Required | Required | Required | Required |
| `keyword_name` | Required | Required | Required | Required |
| `keyword_args` | Required | Required | Required | Required |
| `robot_code_line` | Required | Required | Required | Required |
| `dom_tree` | Required | Useful | Useful | Required |
| `failed_locator` | Required | Useful | N/A | N/A |
| `full_test_case` | Useful | Useful | Required | Useful |
| `screenshot_path` | Useful | Useful | Useful | Required |
| `user_stories` | N/A | N/A | Required | Useful |
| `expected_value` | N/A | N/A | Required | N/A |
| `actual_value` | N/A | N/A | Required | N/A |
| `wait_settings` | N/A | Required | N/A | N/A |
| `page_load_state` | N/A | Required | N/A | N/A |
| `form_metadata` | N/A | N/A | N/A | Required |
| `validation_messages` | N/A | N/A | N/A | Required |

### 16.3 Context Strategy Pattern

```python
# File: context_retrieving/strategies/base_context_strategy.py

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from robot import result, running

from SelfhealingAgents.self_healing_system.context_retrieving.library_dom_utils.base_dom_utils import (
    BaseDomUtils,
)


class BaseContextStrategy(ABC):
    """Abstract base for healing-type-specific context gathering."""

    @abstractmethod
    def gather(
        self,
        data: running.Keyword,
        result_: result.Keyword,
        dom_utility: BaseDomUtils | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Gather context specific to a healing type.

        Returns:
            Dictionary of field_name -> value pairs for HealingPayload.
        """
```

#### 16.3.1 LocatorContextStrategy

```python
# File: context_retrieving/strategies/locator_context_strategy.py

class LocatorContextStrategy(BaseContextStrategy):
    """Context strategy for locator healing (extracts current behavior)."""

    def gather(
        self,
        data: running.Keyword,
        result_: result.Keyword,
        dom_utility: BaseDomUtils | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if dom_utility is None:
            raise ValueError("LocatorContextStrategy requires dom_utility")

        return {
            "dom_tree": dom_utility.get_dom_tree(),
            "failed_locator": BuiltIn().replace_variables(result_.args[0]),
            "healing_type_hint": HealingType.LOCATOR,
        }
```

#### 16.3.2 Context Strategy Factory

```python
# File: context_retrieving/strategies/context_strategy_factory.py

from SelfhealingAgents.self_healing_system.error_classification.healing_types import (
    HealingType,
)

_STRATEGY_REGISTRY: dict[HealingType, type[BaseContextStrategy]] = {
    HealingType.LOCATOR: LocatorContextStrategy,
    HealingType.TIMING: TimingContextStrategy,
    HealingType.ASSERTION: AssertionContextStrategy,
    HealingType.MANDATORY_FIELD: MandatoryFieldContextStrategy,
}


class ContextStrategyFactory:
    """Factory for creating context strategies."""

    @staticmethod
    def create(healing_type: HealingType) -> BaseContextStrategy:
        strategy_cls = _STRATEGY_REGISTRY.get(healing_type)
        if strategy_cls is None:
            raise ValueError(f"Unknown healing type: {healing_type}")
        return strategy_cls()

    @staticmethod
    def create_or_default(
        healing_type: HealingType | None,
    ) -> BaseContextStrategy:
        """Create strategy, defaulting to locator for unknown types."""
        if healing_type is None or healing_type not in _STRATEGY_REGISTRY:
            return LocatorContextStrategy()
        return _STRATEGY_REGISTRY[healing_type]()
```

### 16.4 Screenshot Capture

```python
# File: context_retrieving/screenshot_capturer.py

from typing import Protocol
import tempfile
from pathlib import Path
from robot.libraries.BuiltIn import BuiltIn


class ScreenshotCapturer(Protocol):
    """Protocol for library-specific screenshot capture."""

    def capture(self) -> str | None:
        """Capture screenshot and return file path, or None on failure."""
        ...


class SeleniumScreenshotCapturer:
    def capture(self) -> str | None:
        try:
            lib = BuiltIn().get_library_instance("SeleniumLibrary")
            path = Path(tempfile.mkdtemp()) / "healing_screenshot.png"
            lib.capture_page_screenshot(str(path))
            return str(path)
        except Exception:
            return None


class BrowserScreenshotCapturer:
    def capture(self) -> str | None:
        try:
            lib = BuiltIn().get_library_instance("Browser")
            path = Path(tempfile.mkdtemp()) / "healing_screenshot.png"
            lib.take_screenshot(str(path))
            return str(path)
        except Exception:
            return None


_CAPTURER_REGISTRY = {
    "selenium": SeleniumScreenshotCapturer,
    "browser": BrowserScreenshotCapturer,
}


def create_screenshot_capturer(library_type: str) -> ScreenshotCapturer | None:
    cls = _CAPTURER_REGISTRY.get(library_type)
    return cls() if cls else None
```

### 16.5 User Story Integration

```python
# File: context_retrieving/user_story_retriever.py

from pathlib import Path


class KeywordUserStoryRetriever:
    """Retrieves user stories using keyword-based search."""

    def __init__(self, stories_path: str) -> None:
        self._path = Path(stories_path)
        self._stories: list[dict] | None = None

    def retrieve(
        self,
        test_name: str,
        keyword_name: str,
        max_stories: int = 3,
    ) -> list[str]:
        if self._stories is None:
            self._stories = self._load_stories()

        search_tokens = set(
            token.lower()
            for token in (test_name + " " + keyword_name).split()
            if len(token) >= 3
        )

        scored = []
        for story in self._stories:
            content_lower = story["content"].lower()
            score = sum(1 for token in search_tokens if token in content_lower)
            if score > 0:
                scored.append((score, story["content"]))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [content for _, content in scored[:max_stories]]

    def _load_stories(self) -> list[dict]:
        # Load from .md and .json files in the configured path
        ...
```

### 16.6 Token Budget Management

The token budget system ensures context does not exceed model limits. Each healing
type defines priority-ordered fields with truncation strategies.

```python
# File: context_retrieving/token_budget.py

from typing import Any, Callable


ContextPriority = list[tuple[str, Callable[[Any, int], Any] | None]]


def estimate_tokens(text: str) -> int:
    """Estimate tokens using ~3 chars/token heuristic (conservative)."""
    return len(text) // 3


def apply_token_budget(
    payload_data: dict[str, Any],
    priorities: ContextPriority,
    total_budget: int,
) -> dict[str, Any]:
    """Apply token budget by truncating low-priority fields.

    Args:
        payload_data: Raw payload field values.
        priorities: Priority-ordered list of (field, truncate_fn).
        total_budget: Maximum total tokens.

    Returns:
        Modified payload_data with fields truncated as needed.
    """
    remaining = total_budget
    result = payload_data.copy()

    for field_name, truncate_fn in priorities:
        value = result.get(field_name)
        if value is None:
            continue

        field_tokens = estimate_tokens(str(value))
        if field_tokens <= remaining:
            remaining -= field_tokens
        elif truncate_fn is not None:
            result[field_name] = truncate_fn(value, remaining)
            remaining = 0
        # High-priority fields without truncate_fn are kept anyway

    return result
```

**Token budget split:** The `total_tokens_limit` configuration applies to the combined
input context. Output token limits are handled separately by pydantic-ai's `UsageLimits`.
For a 6000-token budget, approximately 4000 tokens are allocated to input context and
2000 to expected output generation.

### 16.7 Reporting Extension

```python
# File: schemas/internal_state/healing_report_data.py

from pydantic import Field

from SelfhealingAgents.self_healing_system.schemas.internal_state.report_data import (
    ReportData,
)


class HealingReportData(ReportData):
    """Extended report data for multi-healing-type reporting."""

    healing_type: str = Field("locator", description="The healing type used.")
    classification_confidence: float | None = Field(
        None, description="Error classifier confidence."
    )
    context_fields_used: list[str] = Field(
        default_factory=list, description="HealingPayload fields that were populated."
    )
    screenshot_captured: bool = Field(
        False, description="Whether a screenshot was captured."
    )
    token_budget_used: int | None = Field(
        None, description="Approximate tokens consumed."
    )
```

### 16.8 Revised DDD Bounded Context Map

```
+------------------------------------------------------------------------------+
|                              Self-Healing System                              |
|                                                                              |
|  +------------+  +------------+  +---------------+  +-------------------+    |
|  |  Provider  |->|  Output    |<-|  Agent        |<-| Error             |    |
|  |  Context   |  |  Strategy  |  |  Orchestration|  | Classification    |    |
|  +------------+  +------------+  +---------------+  +-------------------+    |
|         |              |                |                    |               |
|  +------------+  +------------+  +---------------+  +-------------------+    |
|  | Config     |  |  Schema    |  |  Context      |  | Reporting         |    |
|  | Context    |  |  Context   |  |  Enrichment   |  | Context           |    |
|  +------------+  +------------+  +---------------+  +-------------------+    |
+------------------------------------------------------------------------------+
```

| Context | Responsibility |
|---------|---------------|
| **Provider** | Model creation, provider-specific adapters |
| **Output Strategy** | Output mode selection, fallback logic |
| **Agent Orchestration** | Agent dispatch, healing type routing |
| **Error Classification** | Tier 1/2 classification, pattern matching |
| **Configuration** | Environment loading, capability mapping |
| **Schema** | Response models, HealingPayload, HealingResponse |
| **Context Enrichment** | Strategy-based gathering, screenshots, user stories |
| **Reporting** | Multi-type report generation |

### 16.9 Unified Phased Delivery

| Phase | Name | Scope |
|-------|------|-------|
| **1** | ADR-001a-e | Provider abstraction, output strategy, config, orchestrator, schema (existing sections 4-8) |
| **2** | Healing Type Foundation | `BaseHealingAgent` ABC, `HealingPayload` flat schema, `ErrorClassification`, `HealingAgentRegistry`, refactor `BaseLocatorAgent` |
| **3** | Error Classification | `PatternRegistry`, deterministic rules, `ErrorClassifier` Tier 1 |
| **4** | Context Enrichment | `BaseContextStrategy`, `LocatorContextStrategy`, `RobotCtxRetriever` changes |
| **5** | First New Type (Timing) | `TimingAgent`, `TimingContextStrategy`, `TimingRetryStrategy` |
| **6** | LLM Classification | `LLMClassifier` Tier 2, union output types, confidence routing |
| **7** | Remaining Types | `AssertionAgent`, `MandatoryFieldAgent`, screenshots, user stories, token budget |

**Phase dependencies:**
- Phase 2 depends on Phase 1 (provider abstraction needed for agents)
- Phase 3 depends on Phase 2 (classification uses HealingType enum)
- Phase 4 depends on Phase 2 (strategies populate HealingPayload)
- Phase 5 depends on Phases 3 and 4 (timing agent needs classification and context)
- Phase 6 depends on Phase 3 (LLM classifier extends ErrorClassifier)
- Phase 7 depends on all previous phases

### 16.10 Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| `HealingPayload` schema drift from `PromptPayload` | Low | High | Subclass relationship with model validator ensures sync |
| Context strategy raises exception | Medium | High | Wrap in try/except, fall back to core fields |
| Screenshot capture fails | Medium | Low | Screenshots optional except for mandatory field healing |
| User story retriever returns irrelevant stories | Medium | Medium | Limit to top 3, provide max_tokens budget |
| Token budget estimation inaccuracy | Low | Medium | Use conservative 3 chars/token, opt-in tiktoken |
| Non-OpenAI models fail on new schemas | Medium | High | All schemas follow flat pattern validated in ADR-001b/f |
| Backward compatibility regression | Low | High | Test classifier output against existing is_failed_locator_error() |
| LLM classification adds latency | Medium | Medium | Tier 2 only for ambiguous errors (~15%), use fast model |

### 16.11 Open Questions

1. **Should `HealingPayload` use `extra="allow"`?** Current design uses default
   (`extra="ignore"`). Using `extra="allow"` enables forward compatibility but loses
   type safety. Decision deferred to implementation.

2. **Should token budget use tiktoken?** tiktoken adds dependency and is OpenAI-specific.
   Current design uses character heuristic. Can add tiktoken as optional if needed.

3. **Should context strategies run in parallel?** Current design is synchronous. For
   timing healing (DOM + network + visibility), parallel gathering could reduce latency.
   Async strategies deferred to future iteration.

4. **How should error classifier confidence propagate?** The classifier produces
   confidence scores. These should flow through to `HealingReportData` for observability.
   Current design includes this path.
