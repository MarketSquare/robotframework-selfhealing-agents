from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.azure import AzureProvider
from pydantic_ai.providers.openai import OpenAIProvider

from RobotAid.self_healing_system.clients.azure_client import AzureClient
from RobotAid.utils.client_settings import ClientSettings


# only a temporary method for handling different clients - especially since azure behaves differently in pydanticAI
def get_model(
    provider: str, model: str, client_settings: ClientSettings
) -> None | OpenAIModel:
    """Returns model/pydanticAI-string based on llm_provider defined by user.

    Args:
        provider (str): Provider for LLM defined by user.
        model (str): LLM name.
        client_settings (ClientSettings): Instance of ClientSettings containing user defined client configuration.

    Returns:
        (None | OpenAIModel]: Model or pydanticAI string of model depending on llm-provider..
    """
    if provider == "azure":
        return OpenAIModel(
            model_name=model,
            provider=AzureProvider(openai_client=AzureClient.get_client_instance()),
        )
    if provider == "openai":
        return OpenAIModel(
            model_name=model,
            provider=OpenAIProvider(
                base_url=client_settings.base_url,
                api_key=client_settings.openai_api_key,
            ),
        )
    return None
