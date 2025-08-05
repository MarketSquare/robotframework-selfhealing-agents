from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from RobotAid.utils.cfg import Cfg


def openai_builder(model_name: str, cfg: Cfg) -> OpenAIModel:
    return OpenAIModel(
        model_name=model_name,
        provider=OpenAIProvider(
            api_key=cfg.openai_api_key,
            base_url=cfg.base_url,
        ),
    )