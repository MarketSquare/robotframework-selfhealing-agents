from __future__ import annotations
import yaml
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError, ConfigDict


class SystemSettings(BaseModel):
    """General system settings for the self-healing system.

    Attributes:
        enabled (bool): Whether the RobotFramework listener should trigger self-healing.
        max_retries (int): Maximum number of retry attempts per failure point.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(..., description="True if RF listener should trigger the self-healing system")
    max_retries: int = Field(3, ge=0, description="Maximum number of retries to heal the current failure point")


class OrchestratorAgentSettings(BaseModel):
    """LLM settings for the orchestrator agent.

    Attributes:
        provider (str): Name of the LLM provider.
        model (str): Name of the LLM model.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str = Field("openai", description="Name of the LLM provider")
    model: str = Field("gpt-4o", description="Name of the LLM model")


class LocatorAgentSettings(BaseModel):
    """LLM settings for the locator agent.

    Attributes:
        provider (str): Name of the LLM provider.
        model (str): Name of the LLM model.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str = Field("openai", description="Name of the LLM provider")
    model: str = Field("gpt-4o", description="Name of the LLM model")


class AppSettings(BaseModel):
    """All application settings, loaded from YAML and validated by Pydantic.

    Attributes:
        system (SystemSettings): General system settings.
        orchestrator_agent (OrchestratorAgentSettings): Settings for the orchestrator LLM agent.
        locator_agent (LocatorAgentSettings): Settings for the locator LLM agent.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    system: SystemSettings
    orchestrator_agent: OrchestratorAgentSettings
    locator_agent: LocatorAgentSettings

    @classmethod
    def from_yaml(cls, path: str | Path) -> AppSettings:
        """Load and validate application settings from a YAML file.

        Args:
            path (str | Path): Path to the YAML configuration file.

        Returns:
            (AppSettings): Instance of AppSettings containing user defined configuration.

        Raises:
            FileNotFoundError: If the file does not exist or is unreadable.
            ValueError: If the YAML root is not a mapping.
            ValidationError: If any field fails Pydantic validation.
        """
        yaml_path = Path(path)
        content = yaml_path.read_text()
        raw = yaml.safe_load(content)

        if not isinstance(raw, dict):
            raise ValueError(f"Expected top-level dict in config, got {type(raw).__name__}")

        try:
            return cls.model_validate(raw)
        except ValidationError as e:
            raise ValidationError(f"Config validation error: {e}") from e
