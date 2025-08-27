from typing import Dict, Callable
from importlib.metadata import entry_points, EntryPoints

from pydantic_ai.models.openai import OpenAIModel

from SelfhealingAgents.utils.cfg import Cfg


class ModelFactory:
    """Factory for creating language model instances based on provider and configuration.

    This class discovers available model provider entry points (set in pyproject.toml) and allows instantiation
    of models by provider name, model name, and configuration.

    Attributes:
        _builders (Dict[str, Callable[[str, Cfg], OpenAIModel]]):
            Mapping of provider names to their builder callables, discovered from entry points.
    """
    def __init__(self) -> None:
        """Initializes the ModelFactory and loads available model provider entry points.

        Discovers all entry points registered under the 'SelfhealingAgents.llm_model_providers'
        group (set in pyproject.toml) and stores their builder callables for later use.
        """
        eps: EntryPoints = entry_points(group="SelfhealingAgents.llm_model_providers")
        self._builders: Dict[str, Callable[[str, Cfg], OpenAIModel]] = {
            ep.name: ep.load()
            for ep in eps
        }

    def create_model(self, provider: str, model_name: str, cfg: Cfg) -> OpenAIModel:
        """Creates a language model instance for the specified provider and configuration.

        Args:
            provider: The name of the language model provider (e.g., 'openai').
            model_name: The name of the model to instantiate (e.g., 'gpt-4o-mini').
            cfg: The configuration object containing provider-specific settings.

        Returns:
            An instance of OpenAIModel for the specified provider and model.

        Raises:
            ValueError: If the specified provider is not registered.
        """
        try:
            builder: Callable[[str, Cfg], OpenAIModel] = self._builders[provider]
        except KeyError:
            raise ValueError("Unknown LLM provider: %r" % provider)
        return builder(model_name, cfg)