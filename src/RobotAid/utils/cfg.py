from typing import Any, Optional

from dotenv import find_dotenv, load_dotenv
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings


load_dotenv(find_dotenv(), override=True)


class Cfg(BaseSettings):
    """App settings configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    enable_self_healing: bool = Field(
        False, env="ENABLE_SELF_HEALING",
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
        description="LLM Provider for Orchestrator agent - Options: 'openai', 'azure'."
    )
    orchestrator_agent_model: str = Field(
        "gpt-4o-mini", env="ORCHESTRATOR_AGENT_MODEL",
        description="Model selection for orchestrator agent."
    )
    locator_agent_provider: str = Field(
        "openai", env="LOCATOR_AGENT_PROVIDER",
        description="LLM Provider for Locator agent - Options: 'openai', 'azure'."
    )
    locator_agent_model: str = Field(
        "gpt-4o-mini", env="LOCATOR_AGENT_MODEL",
        description="Model selection for locator agent."
    )
    azure_api_key: Optional[str] = Field(
        None, env="AZURE_API_KEY",
        description="Azure API key"
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

    def __init__(self, **values: Any) -> None:
        """Init.

        Args:
            **values: Arbitrary values for initialization.
        """
        super().__init__(**values)
