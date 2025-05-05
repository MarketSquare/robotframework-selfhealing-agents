from typing import List
from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.models.openai import OpenAIModel

from self_healing_system.clients.llm_client import get_model
from self_healing_system.agents.locator_agent import LocatorAgent
from self_healing_system.schemas import PromptPayload, LocatorHealingResponse


# MVP Orchestrator Agent - will be adjusted to context and when additional agents will be implemented.
class OrchestratorAgent:
    """Routes raw failure text to the appropriate healing tool.

    Attributes:
        llm_provider (str): Provider for LLM defined by user.
        locator_agent (LocatorAgent): LocatorAgent instance.
    """
    def __init__(self, locator_agent: LocatorAgent, llm_provider: str) -> None:
        self.locator_agent: LocatorAgent = locator_agent

        model: None | OpenAIModel | str = get_model(llm_provider)
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
