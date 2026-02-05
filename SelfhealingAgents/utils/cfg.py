from typing import Any, Optional

from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings


class Cfg(BaseSettings):
    """Application settings configuration.

    Loads environment variables and provides strongly-typed configuration options for the application.
    Uses Pydantic BaseSettings for validation and dotenv for environment variable loading.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    enable_self_healing: bool = Field(
        True, env="ENABLE_SELF_HEALING",
        description="True if Self-Healing System should be activated."
    )
    use_llm_for_locator_generation: bool = Field(
        True, env="USE_LLM_FOR_LOCATOR_GENERATION",
        description="True if LLM should be used for locator generation."
    )
    max_retries: int = Field(
        3, gt=0, env="MAX_RETRIES",
        description="Max number of retries."
    )
    orchestrator_agent_provider: str = Field(
        "openai", env="ORCHESTRATOR_AGENT_PROVIDER",
        description="DEPRECATED: No longer used. The orchestrator now uses programmatic routing instead of LLM-based delegation. Kept for backward compatibility with existing .env files. Will be removed in v2.0."
    )
    orchestrator_agent_model: str = Field(
        "gpt-4o-mini", env="ORCHESTRATOR_AGENT_MODEL",
        description="DEPRECATED: No longer used. See orchestrator_agent_provider."
    )
    orchestrator_agent_temperature: float = Field(
        0.1, gt=0, env="ORCHESTRATOR_AGENT_TEMPERATURE",
        description="DEPRECATED: No longer used. See orchestrator_agent_provider."
    )
    locator_agent_provider: str = Field(
        "openai", env="LOCATOR_AGENT_PROVIDER",
        description="LLM Provider for Locator agent - Options: 'openai', 'azure'."
    )
    locator_agent_model: str = Field(
        "gpt-4o-mini", env="LOCATOR_AGENT_MODEL",
        description="Model selection for locator agent."
    )
    locator_agent_temperature: float = Field(
        0.1, gt=0, env="LOCATOR_AGENT_TEMPERATURE"
    )
    request_limit: int = Field(
        5, env="REQUEST_LIMIT",
        description="Request limit for a each agent."
    )
    total_tokens_limit: int = Field(
        6000, env="TOTAL_TOKENS_LIMIT",
        description="Limit of total tokens for each request."
    )
    locator_type: str = Field(
        "css", env="LOCATOR_TYPE",
        description="Locator type restriction for suggestions of model."
    )
    report_directory: Optional[str] = Field(
        None, env="REPORT_DIRECTORY",
        description="Path to the report directory."
    )
    is_rerun_activated: Optional[bool] = Field(
        False, env="IS_RERUN_ACTIVATED",
        description="Boolean if Rerun option is activated. If True, Report folder will not be deleted to avoid overwriting the initial run."
    )

    # --- New fields for non-OpenAI compatibility (ADR-001c) ---

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

    azure_api_key: Optional[str] = Field(
        None, env="AZURE_API_KEY",
        description="Azure API key"
    )
    azure_api_version: Optional[str] = Field(
        None, env="AZURE_API_VERSION",
        description="Azure API Version"
    )
    azure_endpoint: Optional[str] = Field(
        None, env="AZURE_ENDPOINT",
        description="Azure endpoint URL"
    )
    openai_api_key: Optional[str] = Field(
        None, env="OPENAI_API_KEY",
        description="OpenAI API key"
    )
    base_url: Optional[str] = Field(
        None, env="BASE_URL",
        description="Base URL endpoint"
    )
    litellm_api_key: Optional[str] = Field(
        None, env="LITELLM_API_KEY",
        description="LiteLLM API key"
    )

    def __init__(self, **values: Any) -> None:
        """Initializes the Cfg settings object.

        Args:
            **values: Arbitrary keyword arguments for settings initialization and static checking.
        """
        super().__init__(**values)
