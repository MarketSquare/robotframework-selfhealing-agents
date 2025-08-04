from openai import AsyncAzureOpenAI
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.azure import AzureProvider
from pydantic_ai.providers.openai import OpenAIProvider

from RobotAid.utils.cfg import Cfg


def get_client_model(
    provider: str, model: str, cfg: Cfg
) -> None | OpenAIModel:
    """Returns model/pydanticAI-string based on llm_provider defined by user.

    Args:
        provider (str): Provider for LLM defined by user.
        model (str): LLM name.
        cfg: Instance of Cfg config class containing user defined app configuration.

    Returns:
        (None | OpenAIModel]: Model or pydanticAI string of model depending on llm-provider..
    """
    if provider == "azure":
        return OpenAIModel(
            model_name=model,
            provider=AzureProvider(
                openai_client=AsyncAzureOpenAI(
                    api_key=cfg.azure_api_key,
                    api_version=cfg.azure_api_version,
                    azure_endpoint=cfg.azure_endpoint,
                )
            )
        )

    if provider == "openai":
        return OpenAIModel(
            model_name=model,
            provider=OpenAIProvider(
                base_url=cfg.base_url,
                api_key=cfg.openai_api_key,
            ),
        )
    return None
