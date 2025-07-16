from typing import Any, Optional

from dotenv import find_dotenv, load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv(find_dotenv(), override=True)


class ClientSettings(BaseSettings):
    """Client env configuration."""

    azure_api_key: Optional[str] = Field(
        None, env="AZURE_API_KEY", description="Azure API key"
    )
    azure_endpoint: Optional[str] = Field(
        None, env="AZURE_ENDPOINT", description="Azure endpoint URL"
    )
    openai_api_key: Optional[str] = Field(
        None, env="OPENAI_API_KEY", description="OpenAI API key"
    )
    base_url: Optional[str] = Field(
        None, env="BASE_URL", description="Base URL endpoint"
    )

    def __init__(self, **values: Any) -> None:
        """Initialize the ClientSettings.

        Args:
            **values: Arbitrary keyword arguments for initialization.
        """
        super().__init__(**values)
