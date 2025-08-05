from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from RobotAid.utils.cfg import Cfg


def litellm_builder(model_name: str, cfg: Cfg) -> OpenAIModel:
    endpoint = cfg.base_url.rstrip("/") + "/v1/chat/completions"
    return OpenAIModel(
        model_name=model_name,
        provider=OpenAIProvider(
            api_key=cfg.litellm_api_key,
            base_url=endpoint,
        ),
    )