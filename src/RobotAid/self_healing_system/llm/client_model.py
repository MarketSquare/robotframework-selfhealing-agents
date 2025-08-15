from pydantic_ai.models.openai import OpenAIModel

from RobotAid.utils.cfg import Cfg
from RobotAid.self_healing_system.llm.model_factory import ModelFactory


def get_client_model(*, provider: str, model: str, cfg: Cfg) -> OpenAIModel | None:
    factory: ModelFactory = ModelFactory()
    try:
        return factory.create_model(provider, model, cfg)
    except ValueError:
        return None
