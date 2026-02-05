"""Integration tests for provider compatibility.

Tests for ADR-001 provider abstraction layer integration.
These tests verify the components work together correctly.
"""
import pytest
from unittest.mock import MagicMock, patch

from SelfhealingAgents.utils.cfg import Cfg


class TestProviderIntegration:
    """Integration tests for provider builders with output strategy."""

    @pytest.fixture
    def base_cfg(self):
        """Create a base configuration for testing."""
        return {
            "enable_self_healing": True,
            "use_llm_for_locator_generation": True,
            "max_retries": 3,
            "locator_agent_provider": "openai",
            "locator_agent_model": "gpt-4o-mini",
            "locator_agent_temperature": 0.1,
            "orchestrator_agent_provider": "openai",
            "orchestrator_agent_model": "gpt-4o-mini",
            "orchestrator_agent_temperature": 0.1,
            "request_limit": 5,
            "total_tokens_limit": 6000,
            "locator_type": "css",
            "openai_api_key": "test-key",
            "strict_tool_definitions": True,
            "output_mode": "auto",
        }

    def test_openai_provider_with_native_output(self, base_cfg):
        """OpenAI provider uses NativeOutput in auto mode."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import resolve_structured_output_type
        from pydantic_ai.output import NativeOutput
        from pydantic import BaseModel

        class TestSchema(BaseModel):
            value: str

        cfg = MagicMock()
        cfg.output_mode = "auto"

        result = resolve_structured_output_type(TestSchema, cfg, "openai")

        assert isinstance(result, NativeOutput)

    def test_openrouter_provider_with_tool_output(self, base_cfg):
        """OpenRouter provider uses ToolOutput in auto mode."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import resolve_structured_output_type
        from pydantic import BaseModel

        class TestSchema(BaseModel):
            value: str

        cfg = MagicMock()
        cfg.output_mode = "auto"

        result = resolve_structured_output_type(TestSchema, cfg, "openrouter")

        # ToolOutput returns bare class
        assert result is TestSchema

    def test_ollama_provider_with_prepare_tools_hook(self, base_cfg):
        """Ollama provider gets prepare_tools hook."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import make_prepare_tools_hook

        cfg = MagicMock()

        hook = make_prepare_tools_hook("ollama", cfg)

        assert hook is not None
        assert callable(hook)


class TestErrorClassificationIntegration:
    """Integration tests for error classification pipeline."""

    def test_classify_selenium_locator_error(self):
        """Selenium locator errors are classified correctly."""
        from SelfhealingAgents.self_healing_system.error_classification import (
            classify_error,
            HealingType,
        )

        error_msg = "Element with locator 'css:#submit-btn' not found."
        result = classify_error(error_msg)

        assert result.healing_type == HealingType.LOCATOR
        assert result.tier == 1
        assert result.confidence == 1.0

    def test_classify_browser_locator_error(self):
        """Browser library locator errors are classified correctly."""
        from SelfhealingAgents.self_healing_system.error_classification import (
            classify_error,
            HealingType,
        )

        error_msg = "Timeout 10000ms exceeded. waiting for locator('#btn')"
        result = classify_error(error_msg)

        # This could be LOCATOR or TIMING depending on pattern priority
        assert result.healing_type in (HealingType.LOCATOR, HealingType.TIMING)

    def test_classify_timeout_error(self):
        """Timeout errors are classified as TIMING."""
        from SelfhealingAgents.self_healing_system.error_classification import (
            classify_error,
            HealingType,
        )

        error_msg = "TimeoutException: Operation timed out after 30 seconds"
        result = classify_error(error_msg)

        assert result.healing_type == HealingType.TIMING


class TestCfgNewFields:
    """Tests for new configuration fields."""

    def test_cfg_has_strict_tool_definitions(self):
        """Cfg has strict_tool_definitions field with default True."""
        # Create minimal config
        import os
        os.environ["OPENAI_API_KEY"] = "test"

        try:
            cfg = Cfg()
            assert hasattr(cfg, "strict_tool_definitions")
            assert cfg.strict_tool_definitions is True
        finally:
            del os.environ["OPENAI_API_KEY"]

    def test_cfg_has_output_mode(self):
        """Cfg has output_mode field with default 'auto'."""
        import os
        os.environ["OPENAI_API_KEY"] = "test"

        try:
            cfg = Cfg()
            assert hasattr(cfg, "output_mode")
            assert cfg.output_mode == "auto"
        finally:
            del os.environ["OPENAI_API_KEY"]
