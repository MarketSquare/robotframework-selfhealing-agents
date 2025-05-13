import os
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI


class AzureClient:
    """Class to access azure endpoint for pydanticAI."""
    @staticmethod
    def get_client_instance() -> AsyncAzureOpenAI:
        """Returns azure client instance with user configs.

        Returns:
            (AsyncAzureOpenAI): Azure client instance.
        """
        load_dotenv()
        return AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_API_KEY"),
            api_version="2024-06-01",
            azure_endpoint=os.getenv("AZURE_ENDPOINT")
        )

