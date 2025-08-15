from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from RobotAid.utils.cfg import Cfg


def openai_builder(model_name: str, cfg: Cfg) -> OpenAIModel:
    """Creates an OpenAIModel instance using the specified model name and configuration.

    Instantiates an OpenAIModel with the given model name and configuration settings,
    including API key and base URL from the provided Cfg object.

    Args:
        model_name: The name of the OpenAI model to use (e.g., 'gpt-4o-mini').
        cfg: The configuration object containing OpenAI API credentials and settings.

    Returns:
        An instance of OpenAIModel configured with the specified model name and provider.
    """
    return OpenAIModel(
        model_name=model_name,
        provider=OpenAIProvider(
            api_key=cfg.openai_api_key,
            base_url=cfg.base_url,
        ),
    )