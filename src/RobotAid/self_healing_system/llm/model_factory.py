from typing import Dict, Callable
from importlib.metadata import entry_points, EntryPoints

from pydantic_ai.models.openai import OpenAIModel

from RobotAid.utils.cfg import Cfg


class ModelFactory:
    def __init__(self) -> None:
        eps: EntryPoints = entry_points(group="robot_aid.llm_model_providers")
        self._builders: Dict[str, Callable[[str, Cfg], OpenAIModel]] = {
            ep.name: ep.load()
            for ep in eps
        }

    def create_model(self, provider: str, model_name: str, cfg: Cfg) -> OpenAIModel:
        try:
            builder: Callable[[str, Cfg], OpenAIModel] = self._builders[provider]
        except KeyError:
            raise ValueError("Unknown LLM provider: %r" % provider)
        return builder(model_name, cfg)