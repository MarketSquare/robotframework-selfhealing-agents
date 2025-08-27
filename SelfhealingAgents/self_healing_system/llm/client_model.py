from pydantic_ai.models.openai import OpenAIModel

from SelfhealingAgents.utils.cfg import Cfg
from SelfhealingAgents.utils.logging import log
from SelfhealingAgents.self_healing_system.llm.model_factory import ModelFactory


@log
def get_client_model(*, provider: str, model: str, cfg: Cfg) -> OpenAIModel | None:
    """Creates and returns a language model client for the specified provider and model.

    Instantiates a ModelFactory and attempts to create a language model client
    using the given provider, model name, and configuration. If the provider is
    unknown, returns None.

    Args:
        provider: The name of the language model provider (e.g., 'openai').
        model: The name of the model to instantiate (e.g., 'gpt-4o-mini').
        cfg: The configuration object containing provider-specific settings.

    Returns:
        An instance of OpenAIModel if the provider is recognized; otherwise, None.
    """
    factory: ModelFactory = ModelFactory()
    try:
        return factory.create_model(provider, model, cfg)
    except ValueError:
        return None
