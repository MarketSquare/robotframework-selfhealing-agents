from typing import List
from pydantic_ai import Agent
from pydantic_ai.usage import UsageLimits
from pydantic_ai.agent import AgentRunResult

from self_healing_system.clients.llm_client import get_model
from self_healing_system.schemas import PromptPayload, LocatorSuggestionsResponse


# MVP LocatorAgent - prompt will be adjusted based on provided context.
class LocatorAgent:
    """Produces locator alternatives.

    Attributes:
        llm_provider (str): Provider for LLM defined by user.
        max_retries (int): Maximum number of request retries.
        usage_limits (UsageLimits): Usage token and request limits.
    """
    def __init__(
        self,
        llm_provider: str,
        max_retries: int = 3,
        usage_limits: UsageLimits = UsageLimits(request_limit=5, total_tokens_limit=2000)
    ) -> None:
        self.max_retries: int = max_retries
        self.usage_limits: UsageLimits = usage_limits

        self.generation_agent: Agent[PromptPayload, LocatorSuggestionsResponse] = (
            Agent[PromptPayload, LocatorSuggestionsResponse](
            model=get_model(llm_provider=llm_provider),
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
        gen_resp: AgentRunResult = await self.generation_agent.run(
            failure_details,
            usage_limits=self.usage_limits
        )
        return gen_resp.output.suggestions
