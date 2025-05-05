import os
from typing import List
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from pydantic_ai import Agent
from pydantic_ai.usage import UsageLimits
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.azure import AzureProvider

from self_healing_system.schemas import PromptPayload, LocatorSuggestionsResponse


load_dotenv()
azure_client: AsyncAzureOpenAI = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-06-01",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)


class LocatorAgent:
    """Produces locator alternatives.

    Attributes:
        max_retries (int): Maximum number of request retries.
        usage_limits (UsageLimits): Usage token and request limits.
    """
    def __init__(
        self,
        max_retries: int = 3,
        usage_limits: UsageLimits = UsageLimits(request_limit=5, total_tokens_limit=2000)
    ) -> None:
        self.max_retries: int = max_retries
        self.usage_limits: UsageLimits = usage_limits

        model: OpenAIModel = OpenAIModel(
            model_name="gpt-4o",
            provider=AzureProvider(openai_client=azure_client)
        )

        self.generation_agent: Agent[PromptPayload, LocatorSuggestionsResponse] = (
            Agent[PromptPayload, LocatorSuggestionsResponse](
            model=model,
            system_prompt=(
                'Given failure_details, return JSON with `suggestions`: list of locators.'
            ),
            deps_type=PromptPayload,
            output_type=LocatorSuggestionsResponse
        ))

    async def heal_async(self, failure_details: str) -> List[str]:
        """Generate suggestions for fixing broken locator.

        Args:
            failure_details (str): Test suite failure details.

        Returns:
            (List): Suggestions for fixed locators.
        """
        gen_resp = await self.generation_agent.run(
            failure_details,
            usage_limits=self.usage_limits
        )
        return gen_resp.output.suggestions
