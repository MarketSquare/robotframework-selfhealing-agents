import os
from typing import List
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.azure import AzureProvider

from self_healing_system.agents.locator_agent import LocatorAgent
from self_healing_system.schemas import PromptPayload, LocatorHealingResponse


load_dotenv()
azure_client: AsyncAzureOpenAI = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-06-01",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)


class OrchestratorAgent:
    """Routes raw failure text to the appropriate healing tool.

    Attributes:
        locator_agent: LocatorAgent instance.
    """
    def __init__(self, locator_agent: LocatorAgent) -> None:
        self.locator_agent: LocatorAgent = locator_agent

        model: OpenAIModel = OpenAIModel(
            model_name="gpt-4o",
            provider=AzureProvider(openai_client=azure_client)
        )

        self.agent: Agent[PromptPayload, LocatorHealingResponse] = (
            Agent[PromptPayload, LocatorHealingResponse](
            model=model,
            system_prompt=(
                'Based on failure_details, select and run the proper healing tool.',
                'Use `locator_heal` for locator-related failures.'
            ),
            deps_type=PromptPayload,
            output_type=LocatorHealingResponse
        ))

        @self.agent.tool
        async def locator_heal(ctx: RunContext[str], failure_details: str) -> LocatorHealingResponse:
            """Invoke LocatorAgent on raw failure details.

            Args:
                ctx (RunContext): PydanticAI tool context.
                failure_details (str): Test suite failure details.

            Returns:
                (LocatorHealingResponse): List of repaired locator suggestions.
            """
            suggestions: List[str] = await self.locator_agent.heal_async(failure_details)
            return LocatorHealingResponse(suggestions=suggestions)

    async def run_async(self, failure_details: str) -> LocatorHealingResponse:
        """Run orchestration on raw failure_details asynchronously.

        Args:
            failure_details (str): Test suite failure details.

        Returns:
            (LocatorHealingResponse): List of repaired locators.
        """
        result: AgentRunResult = await self.agent.run(
            failure_details,
            usage_limits=UsageLimits(request_limit=5, total_tokens_limit=2000)
        )
        return result.output
