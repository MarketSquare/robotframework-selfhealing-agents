from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from SelfhealingAgents.utils.cfg import Cfg


def litellm_builder(model_name: str, cfg: Cfg) -> OpenAIModel:
    """Creates an OpenAIModel instance for LiteLLM using the specified model name and configuration.

    Constructs an OpenAIModel with the given model name and configuration settings,
    using the LiteLLM API key and a base URL endpoint for chat completions.

    Args:
        model_name: The name of the model to use (e.g., 'gpt-4o-mini').
        cfg: The configuration object containing LiteLLM API credentials and settings.

    Returns:
        An instance of OpenAIModel configured for LiteLLM with the specified model name and provider.
    """
    endpoint = cfg.base_url.rstrip("/") + "/v1/chat/completions"
    return OpenAIModel(
        model_name=model_name,
        provider=OpenAIProvider(
            api_key=cfg.litellm_api_key,
            base_url=endpoint,
        ),
    )