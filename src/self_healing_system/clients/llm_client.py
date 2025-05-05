from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.azure import AzureProvider

from self_healing_system.clients.azure_client import AzureClient


# only a temporary method for handling different clients - especially since azure behaves differently in pydanticAI
def get_model(llm_provider: str) -> None | OpenAIModel | str:
    """Returns model/pydanticAI-string based on llm_provider defined by user.

    Args:
        llm_provider (str): Provider for LLM defined by user.

    Returns:
        (None | OpenAIModel | str]: Model or pydanticAI string of model depending on llm-provider..
    """
    if llm_provider == "azure":
        return OpenAIModel(
            model_name="gpt-4o",
            provider=AzureProvider(openai_client=AzureClient.get_client_instance())
        )
    if llm_provider == "openai":
        return "openai:gpt-4o"
    if llm_provider == "google":
        return "google-gla:gemini-1.5-flash"
    return None