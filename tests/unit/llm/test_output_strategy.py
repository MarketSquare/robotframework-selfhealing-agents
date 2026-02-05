"""Unit tests for output strategy module.

Tests for ADR-001b tri-modal output strategy.
"""
import pytest
from unittest.mock import MagicMock, patch

from pydantic import BaseModel, Field


class MockSchema(BaseModel):
    """Mock schema for testing."""
    suggestions: list[str] = Field(default_factory=list)


class TestResolveStructuredOutputType:
    """Tests for resolve_structured_output_type()."""

    def test_native_mode_returns_native_output(self):
        """Output mode 'native' returns NativeOutput wrapper."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import resolve_structured_output_type
        from pydantic_ai.output import NativeOutput

        cfg = MagicMock()
        cfg.output_mode = "native"

        result = resolve_structured_output_type(MockSchema, cfg, "openai")

        assert isinstance(result, NativeOutput)

    def test_tool_mode_returns_bare_class(self):
        """Output mode 'tool' returns bare schema class (ToolOutput default)."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import resolve_structured_output_type

        cfg = MagicMock()
        cfg.output_mode = "tool"

        result = resolve_structured_output_type(MockSchema, cfg, "openrouter")

        assert result is MockSchema

    def test_prompted_mode_returns_prompted_output(self):
        """Output mode 'prompted' returns PromptedOutput wrapper."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import resolve_structured_output_type
        from pydantic_ai.output import PromptedOutput

        cfg = MagicMock()
        cfg.output_mode = "prompted"

        result = resolve_structured_output_type(MockSchema, cfg, "ollama")

        assert isinstance(result, PromptedOutput)

    def test_auto_mode_openai_returns_native(self):
        """Auto mode for OpenAI returns NativeOutput."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import resolve_structured_output_type
        from pydantic_ai.output import NativeOutput

        cfg = MagicMock()
        cfg.output_mode = "auto"

        result = resolve_structured_output_type(MockSchema, cfg, "openai")

        assert isinstance(result, NativeOutput)

    def test_auto_mode_azure_returns_native(self):
        """Auto mode for Azure returns NativeOutput."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import resolve_structured_output_type
        from pydantic_ai.output import NativeOutput

        cfg = MagicMock()
        cfg.output_mode = "auto"

        result = resolve_structured_output_type(MockSchema, cfg, "azure")

        assert isinstance(result, NativeOutput)

    def test_auto_mode_openrouter_returns_tool(self):
        """Auto mode for OpenRouter returns bare class (ToolOutput)."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import resolve_structured_output_type

        cfg = MagicMock()
        cfg.output_mode = "auto"

        result = resolve_structured_output_type(MockSchema, cfg, "openrouter")

        assert result is MockSchema

    def test_auto_mode_ollama_returns_tool(self):
        """Auto mode for Ollama returns bare class (ToolOutput) by default."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import resolve_structured_output_type

        cfg = MagicMock()
        cfg.output_mode = "auto"

        result = resolve_structured_output_type(MockSchema, cfg, "ollama")

        assert result is MockSchema


class TestMakePrepareToolsHook:
    """Tests for make_prepare_tools_hook()."""

    def test_ollama_returns_hook(self):
        """Ollama provider gets a prepare_tools hook."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import make_prepare_tools_hook

        cfg = MagicMock()

        result = make_prepare_tools_hook("ollama", cfg)

        assert result is not None
        assert callable(result)

    def test_vllm_returns_hook(self):
        """vLLM provider gets a prepare_tools hook."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import make_prepare_tools_hook

        cfg = MagicMock()

        result = make_prepare_tools_hook("vllm", cfg)

        assert result is not None
        assert callable(result)

    def test_openai_returns_none(self):
        """OpenAI provider does not need a prepare_tools hook."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import make_prepare_tools_hook

        cfg = MagicMock()

        result = make_prepare_tools_hook("openai", cfg)

        assert result is None

    def test_openrouter_returns_none(self):
        """OpenRouter provider does not need a prepare_tools hook."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import make_prepare_tools_hook

        cfg = MagicMock()

        result = make_prepare_tools_hook("openrouter", cfg)

        assert result is None


class TestStripStrictFromSchema:
    """Tests for _strip_strict_from_schema()."""

    def test_removes_strict_key(self):
        """Strict key is removed from schema."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import _strip_strict_from_schema

        schema = {"type": "object", "strict": True}
        _strip_strict_from_schema(schema)

        assert "strict" not in schema

    def test_removes_additional_properties(self):
        """additionalProperties key is removed from schema."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import _strip_strict_from_schema

        schema = {"type": "object", "additionalProperties": False}
        _strip_strict_from_schema(schema)

        assert "additionalProperties" not in schema

    def test_recursively_cleans_nested_properties(self):
        """Nested properties are also cleaned."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import _strip_strict_from_schema

        schema = {
            "type": "object",
            "strict": True,
            "properties": {
                "nested": {
                    "type": "object",
                    "strict": True,
                    "additionalProperties": False,
                }
            }
        }
        _strip_strict_from_schema(schema)

        assert "strict" not in schema
        assert "strict" not in schema["properties"]["nested"]
        assert "additionalProperties" not in schema["properties"]["nested"]

    def test_recursively_cleans_array_items(self):
        """Array items are also cleaned."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import _strip_strict_from_schema

        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "strict": True,
                "additionalProperties": False,
            }
        }
        _strip_strict_from_schema(schema)

        assert "strict" not in schema["items"]
        assert "additionalProperties" not in schema["items"]
