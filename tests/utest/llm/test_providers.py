"""Unit tests for LLM provider builders.

Tests for ADR-001a provider abstraction layer.
"""
import pytest
from unittest.mock import MagicMock, patch, call

from SelfhealingAgents.utils.cfg import Cfg


class TestOpenAIBuilder:
    """Tests for openai_builder."""

    @patch("SelfhealingAgents.self_healing_system.llm.providers.openai_builder.OpenAIChatModel")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.openai_builder.OpenAIProvider")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.openai_builder.OpenAIModelProfile")
    def test_openai_builder_creates_model_with_profile(
        self, mock_profile, mock_provider, mock_model
    ):
        """OpenAI builder creates model with profile from config."""
        from SelfhealingAgents.self_healing_system.llm.providers.openai_builder import openai_builder

        cfg = MagicMock(spec=Cfg)
        cfg.openai_api_key = "test-key"
        cfg.base_url = None
        cfg.strict_tool_definitions = True

        result = openai_builder("gpt-4o-mini", cfg)

        mock_profile.assert_called_once_with(openai_supports_strict_tool_definition=True)
        mock_provider.assert_called_once_with(api_key="test-key", base_url=None)
        mock_model.assert_called_once()
        assert result == mock_model.return_value

    @patch("SelfhealingAgents.self_healing_system.llm.providers.openai_builder.OpenAIChatModel")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.openai_builder.OpenAIProvider")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.openai_builder.OpenAIModelProfile")
    def test_openai_builder_respects_strict_false(
        self, mock_profile, mock_provider, mock_model
    ):
        """OpenAI builder respects strict_tool_definitions=False."""
        from SelfhealingAgents.self_healing_system.llm.providers.openai_builder import openai_builder

        cfg = MagicMock(spec=Cfg)
        cfg.openai_api_key = "test-key"
        cfg.base_url = None
        cfg.strict_tool_definitions = False

        openai_builder("gpt-4o-mini", cfg)

        mock_profile.assert_called_once_with(openai_supports_strict_tool_definition=False)

    @patch("SelfhealingAgents.self_healing_system.llm.providers.openai_builder.OpenAIChatModel")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.openai_builder.OpenAIProvider")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.openai_builder.OpenAIModelProfile")
    def test_openai_builder_passes_base_url(
        self, mock_profile, mock_provider, mock_model
    ):
        """OpenAI builder passes base_url when configured."""
        from SelfhealingAgents.self_healing_system.llm.providers.openai_builder import openai_builder

        cfg = MagicMock(spec=Cfg)
        cfg.openai_api_key = "test-key"
        cfg.base_url = "https://custom.openai.endpoint/v1"
        cfg.strict_tool_definitions = True

        openai_builder("gpt-4o", cfg)

        mock_provider.assert_called_once_with(
            api_key="test-key",
            base_url="https://custom.openai.endpoint/v1"
        )

    @patch("SelfhealingAgents.self_healing_system.llm.providers.openai_builder.OpenAIChatModel")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.openai_builder.OpenAIProvider")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.openai_builder.OpenAIModelProfile")
    def test_openai_builder_passes_model_name(
        self, mock_profile, mock_provider, mock_model
    ):
        """OpenAI builder passes model_name correctly."""
        from SelfhealingAgents.self_healing_system.llm.providers.openai_builder import openai_builder

        cfg = MagicMock(spec=Cfg)
        cfg.openai_api_key = "test-key"
        cfg.base_url = None
        cfg.strict_tool_definitions = True

        openai_builder("gpt-4-turbo", cfg)

        call_kwargs = mock_model.call_args[1]
        assert call_kwargs["model_name"] == "gpt-4-turbo"


class TestOpenRouterBuilder:
    """Tests for openrouter_builder."""

    @patch("SelfhealingAgents.self_healing_system.llm.providers.openrouter_builder.OpenAIChatModel")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.openrouter_builder.OpenRouterProvider")
    def test_openrouter_builder_uses_openrouter_provider(
        self, mock_provider, mock_model
    ):
        """OpenRouter builder uses OpenRouterProvider."""
        from SelfhealingAgents.self_healing_system.llm.providers.openrouter_builder import openrouter_builder

        cfg = MagicMock(spec=Cfg)
        cfg.openai_api_key = "sk-or-test"

        result = openrouter_builder("mistralai/devstral-2512", cfg)

        mock_provider.assert_called_once_with(api_key="sk-or-test")
        mock_model.assert_called_once()
        assert result == mock_model.return_value

    @patch("SelfhealingAgents.self_healing_system.llm.providers.openrouter_builder.OpenAIChatModel")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.openrouter_builder.OpenRouterProvider")
    def test_openrouter_builder_passes_model_name(
        self, mock_provider, mock_model
    ):
        """OpenRouter builder passes model_name correctly."""
        from SelfhealingAgents.self_healing_system.llm.providers.openrouter_builder import openrouter_builder

        cfg = MagicMock(spec=Cfg)
        cfg.openai_api_key = "sk-or-test"

        openrouter_builder("anthropic/claude-3-sonnet", cfg)

        call_kwargs = mock_model.call_args[1]
        assert call_kwargs["model_name"] == "anthropic/claude-3-sonnet"

    @patch("SelfhealingAgents.self_healing_system.llm.providers.openrouter_builder.OpenAIChatModel")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.openrouter_builder.OpenRouterProvider")
    def test_openrouter_builder_does_not_use_profile(
        self, mock_provider, mock_model
    ):
        """OpenRouter builder does not pass profile (uses provider defaults)."""
        from SelfhealingAgents.self_healing_system.llm.providers.openrouter_builder import openrouter_builder

        cfg = MagicMock(spec=Cfg)
        cfg.openai_api_key = "sk-or-test"

        openrouter_builder("google/gemini-pro", cfg)

        call_kwargs = mock_model.call_args[1]
        assert "profile" not in call_kwargs


class TestOllamaBuilder:
    """Tests for ollama_builder."""

    @patch("SelfhealingAgents.self_healing_system.llm.providers.ollama_builder.OpenAIChatModel")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.ollama_builder.OpenAIProvider")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.ollama_builder.OpenAIModelProfile")
    def test_ollama_builder_uses_dummy_api_key(
        self, mock_profile, mock_provider, mock_model
    ):
        """Ollama builder uses 'ollama' as dummy API key."""
        from SelfhealingAgents.self_healing_system.llm.providers.ollama_builder import ollama_builder

        cfg = MagicMock(spec=Cfg)
        cfg.base_url = "http://localhost:11434/v1"

        ollama_builder("qwen3:latest", cfg)

        mock_provider.assert_called_once_with(
            api_key="ollama",
            base_url="http://localhost:11434/v1",
        )

    @patch("SelfhealingAgents.self_healing_system.llm.providers.ollama_builder.OpenAIChatModel")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.ollama_builder.OpenAIProvider")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.ollama_builder.OpenAIModelProfile")
    def test_ollama_builder_always_strict_false(
        self, mock_profile, mock_provider, mock_model
    ):
        """Ollama builder always sets strict=False regardless of config."""
        from SelfhealingAgents.self_healing_system.llm.providers.ollama_builder import ollama_builder

        cfg = MagicMock(spec=Cfg)
        cfg.base_url = None

        ollama_builder("gemma3:12b", cfg)

        mock_profile.assert_called_once_with(openai_supports_strict_tool_definition=False)

    @patch("SelfhealingAgents.self_healing_system.llm.providers.ollama_builder.OpenAIChatModel")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.ollama_builder.OpenAIProvider")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.ollama_builder.OpenAIModelProfile")
    def test_ollama_builder_default_base_url(
        self, mock_profile, mock_provider, mock_model
    ):
        """Ollama builder uses default localhost URL when not configured."""
        from SelfhealingAgents.self_healing_system.llm.providers.ollama_builder import ollama_builder

        cfg = MagicMock(spec=Cfg)
        cfg.base_url = None

        ollama_builder("qwen3:latest", cfg)

        mock_provider.assert_called_once_with(
            api_key="ollama",
            base_url="http://localhost:11434/v1",
        )

    @patch("SelfhealingAgents.self_healing_system.llm.providers.ollama_builder.OpenAIChatModel")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.ollama_builder.OpenAIProvider")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.ollama_builder.OpenAIModelProfile")
    def test_ollama_builder_custom_base_url(
        self, mock_profile, mock_provider, mock_model
    ):
        """Ollama builder uses custom base_url when configured."""
        from SelfhealingAgents.self_healing_system.llm.providers.ollama_builder import ollama_builder

        cfg = MagicMock(spec=Cfg)
        cfg.base_url = "http://ollama.local:8080/v1"

        ollama_builder("llama3:8b", cfg)

        mock_provider.assert_called_once_with(
            api_key="ollama",
            base_url="http://ollama.local:8080/v1",
        )

    @patch("SelfhealingAgents.self_healing_system.llm.providers.ollama_builder.OpenAIChatModel")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.ollama_builder.OpenAIProvider")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.ollama_builder.OpenAIModelProfile")
    def test_ollama_builder_passes_model_name(
        self, mock_profile, mock_provider, mock_model
    ):
        """Ollama builder passes model_name correctly."""
        from SelfhealingAgents.self_healing_system.llm.providers.ollama_builder import ollama_builder

        cfg = MagicMock(spec=Cfg)
        cfg.base_url = None

        ollama_builder("codellama:34b", cfg)

        call_kwargs = mock_model.call_args[1]
        assert call_kwargs["model_name"] == "codellama:34b"


class TestLiteLLMBuilder:
    """Tests for litellm_builder."""

    @patch("SelfhealingAgents.self_healing_system.llm.providers.litellm_builder.OpenAIChatModel")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.litellm_builder.OpenAIProvider")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.litellm_builder.OpenAIModelProfile")
    def test_litellm_builder_creates_model_with_profile(
        self, mock_profile, mock_provider, mock_model
    ):
        """LiteLLM builder creates model with profile from config."""
        from SelfhealingAgents.self_healing_system.llm.providers.litellm_builder import litellm_builder

        cfg = MagicMock(spec=Cfg)
        cfg.litellm_api_key = "litellm-key"
        cfg.base_url = "http://litellm.local:4000"
        cfg.strict_tool_definitions = True

        result = litellm_builder("gpt-4o-mini", cfg)

        mock_profile.assert_called_once_with(openai_supports_strict_tool_definition=True)
        mock_provider.assert_called_once_with(
            api_key="litellm-key",
            base_url="http://litellm.local:4000"
        )
        mock_model.assert_called_once()
        assert result == mock_model.return_value

    @patch("SelfhealingAgents.self_healing_system.llm.providers.litellm_builder.OpenAIChatModel")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.litellm_builder.OpenAIProvider")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.litellm_builder.OpenAIModelProfile")
    def test_litellm_builder_respects_strict_false(
        self, mock_profile, mock_provider, mock_model
    ):
        """LiteLLM builder respects strict_tool_definitions=False."""
        from SelfhealingAgents.self_healing_system.llm.providers.litellm_builder import litellm_builder

        cfg = MagicMock(spec=Cfg)
        cfg.litellm_api_key = "litellm-key"
        cfg.base_url = "http://litellm.local:4000"
        cfg.strict_tool_definitions = False

        litellm_builder("gpt-4o-mini", cfg)

        mock_profile.assert_called_once_with(openai_supports_strict_tool_definition=False)

    @patch("SelfhealingAgents.self_healing_system.llm.providers.litellm_builder.OpenAIChatModel")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.litellm_builder.OpenAIProvider")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.litellm_builder.OpenAIModelProfile")
    def test_litellm_builder_strips_trailing_slash(
        self, mock_profile, mock_provider, mock_model
    ):
        """LiteLLM builder strips trailing slash from base_url."""
        from SelfhealingAgents.self_healing_system.llm.providers.litellm_builder import litellm_builder

        cfg = MagicMock(spec=Cfg)
        cfg.litellm_api_key = "litellm-key"
        cfg.base_url = "http://litellm.local:4000/"
        cfg.strict_tool_definitions = True

        litellm_builder("claude-3-sonnet", cfg)

        mock_provider.assert_called_once_with(
            api_key="litellm-key",
            base_url="http://litellm.local:4000"
        )

    @patch("SelfhealingAgents.self_healing_system.llm.providers.litellm_builder.OpenAIChatModel")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.litellm_builder.OpenAIProvider")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.litellm_builder.OpenAIModelProfile")
    def test_litellm_builder_handles_none_base_url(
        self, mock_profile, mock_provider, mock_model
    ):
        """LiteLLM builder handles None base_url gracefully."""
        from SelfhealingAgents.self_healing_system.llm.providers.litellm_builder import litellm_builder

        cfg = MagicMock(spec=Cfg)
        cfg.litellm_api_key = "litellm-key"
        cfg.base_url = None
        cfg.strict_tool_definitions = True

        litellm_builder("gpt-4o-mini", cfg)

        mock_provider.assert_called_once_with(
            api_key="litellm-key",
            base_url=None
        )

    @patch("SelfhealingAgents.self_healing_system.llm.providers.litellm_builder.OpenAIChatModel")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.litellm_builder.OpenAIProvider")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.litellm_builder.OpenAIModelProfile")
    def test_litellm_builder_passes_model_name(
        self, mock_profile, mock_provider, mock_model
    ):
        """LiteLLM builder passes model_name correctly."""
        from SelfhealingAgents.self_healing_system.llm.providers.litellm_builder import litellm_builder

        cfg = MagicMock(spec=Cfg)
        cfg.litellm_api_key = "litellm-key"
        cfg.base_url = "http://litellm.local:4000"
        cfg.strict_tool_definitions = True

        litellm_builder("azure/gpt-4", cfg)

        call_kwargs = mock_model.call_args[1]
        assert call_kwargs["model_name"] == "azure/gpt-4"


class TestAzureBuilder:
    """Tests for azure_builder."""

    @patch("SelfhealingAgents.self_healing_system.llm.providers.azure_builder.OpenAIModel")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.azure_builder.AzureProvider")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.azure_builder.AsyncAzureOpenAI")
    def test_azure_builder_creates_model_with_azure_provider(
        self, mock_azure_client, mock_provider, mock_model
    ):
        """Azure builder creates model with AzureProvider."""
        from SelfhealingAgents.self_healing_system.llm.providers.azure_builder import azure_builder

        cfg = MagicMock(spec=Cfg)
        cfg.azure_api_key = "azure-key"
        cfg.azure_api_version = "2024-02-15-preview"
        cfg.azure_endpoint = "https://my-resource.openai.azure.com"

        result = azure_builder("gpt-4o-mini", cfg)

        mock_azure_client.assert_called_once_with(
            api_key="azure-key",
            api_version="2024-02-15-preview",
            azure_endpoint="https://my-resource.openai.azure.com"
        )
        mock_provider.assert_called_once()
        mock_model.assert_called_once()
        assert result == mock_model.return_value

    @patch("SelfhealingAgents.self_healing_system.llm.providers.azure_builder.OpenAIModel")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.azure_builder.AzureProvider")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.azure_builder.AsyncAzureOpenAI")
    def test_azure_builder_passes_model_name(
        self, mock_azure_client, mock_provider, mock_model
    ):
        """Azure builder passes model_name correctly."""
        from SelfhealingAgents.self_healing_system.llm.providers.azure_builder import azure_builder

        cfg = MagicMock(spec=Cfg)
        cfg.azure_api_key = "azure-key"
        cfg.azure_api_version = "2024-02-15-preview"
        cfg.azure_endpoint = "https://my-resource.openai.azure.com"

        azure_builder("my-deployment-name", cfg)

        call_kwargs = mock_model.call_args[1]
        assert call_kwargs["model_name"] == "my-deployment-name"

    @patch("SelfhealingAgents.self_healing_system.llm.providers.azure_builder.OpenAIModel")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.azure_builder.AzureProvider")
    @patch("SelfhealingAgents.self_healing_system.llm.providers.azure_builder.AsyncAzureOpenAI")
    def test_azure_builder_uses_openai_model_not_chat_model(
        self, mock_azure_client, mock_provider, mock_model
    ):
        """Azure builder uses OpenAIModel (not OpenAIChatModel)."""
        from SelfhealingAgents.self_healing_system.llm.providers.azure_builder import azure_builder

        cfg = MagicMock(spec=Cfg)
        cfg.azure_api_key = "azure-key"
        cfg.azure_api_version = "2024-02-15-preview"
        cfg.azure_endpoint = "https://my-resource.openai.azure.com"

        azure_builder("gpt-4", cfg)

        # Verify OpenAIModel was called, not OpenAIChatModel
        mock_model.assert_called_once()
