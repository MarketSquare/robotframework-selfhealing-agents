from openai import AsyncAzureOpenAI
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.azure import AzureProvider

from RobotAid.utils.cfg import Cfg


def azure_builder(model_name: str, cfg: Cfg) -> OpenAIModel:
    """Creates an OpenAIModel instance for Azure OpenAI using the specified model name and configuration.

    Instantiates an OpenAIModel with the given model name and AzureProvider, using
    credentials and endpoint information from the provided configuration object.

    Args:
        model_name: The name of the Azure OpenAI model to use (e.g., 'gpt-4o-mini').
        cfg: The configuration object containing Azure API credentials and settings.

    Returns:
        An instance of OpenAIModel configured for Azure OpenAI with the specified model name and provider.
    """
    return OpenAIModel(
        model_name=model_name,
        provider=AzureProvider(
            openai_client=AsyncAzureOpenAI(
                api_key=cfg.azure_api_key,
                api_version=cfg.azure_api_version,
                azure_endpoint=cfg.azure_endpoint,
            )
        ),
    )