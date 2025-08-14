from openai import AsyncAzureOpenAI
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.azure import AzureProvider

from RobotAid.utils.cfg import Cfg


def azure_builder(model_name: str, cfg: Cfg) -> OpenAIModel:
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