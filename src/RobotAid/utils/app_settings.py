from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class SystemSettings(BaseModel):
    """General system settings for the self-healing system.

    Attributes:
        enabled: Whether the RobotFramework listener should trigger self-healing.
        max_retries: Maximum number of retry attempts per failure point.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        ..., description="True if RF listener should trigger the self-healing system"
    )
    max_retries: int = Field(
        3,
        ge=0,
        description="Maximum number of retries to heal the current failure point",
    )


class OrchestratorAgentSettings(BaseModel):
    """LLM settings for the orchestrator agent.

    Attributes:
        provider: Name of the LLM provider.
        model: Name of the LLM model.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str = Field("openai", description="Name of the LLM provider")
    model: str = Field("gpt-4o", description="Name of the LLM model")


class LocatorAgentSettings(BaseModel):
    """LLM settings for the locator agent.

    Attributes:
        provider: Name of the LLM provider.
        model: Name of the LLM model.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str = Field("openai", description="Name of the LLM provider")
    model: str = Field("gpt-4o", description="Name of the LLM model")


class AppSettings(BaseModel):
    """All application settings, loaded from YAML and validated by Pydantic.

    Attributes:
        system: General system settings.
        orchestrator_agent: Settings for the orchestrator LLM agent.
        locator_agent: Settings for the locator LLM agent.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    system: SystemSettings
    orchestrator_agent: OrchestratorAgentSettings
    locator_agent: LocatorAgentSettings

    @classmethod
    def from_yaml(cls, path: str | Path) -> AppSettings:
        """Load and validate application settings from a YAML file.

        Args:
            path: Path to the YAML configuration file.

        Returns:
            Instance of AppSettings containing user defined configuration.

        Raises:
            FileNotFoundError: If the file does not exist or is unreadable.
            ValueError: If the YAML root is not a mapping or validation fails.
            ValidationError: If any field fails Pydantic validation.
        """
        yaml_path = Path(path)
        content = yaml_path.read_text()
        raw = yaml.safe_load(content)

        if not isinstance(raw, dict):
            raise ValueError(
                f"Expected top-level dict in config, got {type(raw).__name__}"
            )

        try:
            return cls.model_validate(raw)
        except ValidationError as e:
            raise ValueError(f"Config validation error: {e}") from e
