from typing import List
from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits
from pydantic_ai.agent import AgentRunResult

from RobotAid.self_healing_system.clients.llm_client import get_model
from RobotAid.self_healing_system.schemas import PromptPayload, LocatorSuggestionsResponse


# MVP LocatorAgent - prompt will be adjusted based on provided context.
class LocatorAgent:
    """Produces alternatives for broken locator.

    Attributes:
        llm_provider (str): Provider for LLM defined by user.
        usage_limits (UsageLimits): Usage token and request limits.
    """
    def __init__(
        self,
        llm_provider: str,
        usage_limits: UsageLimits = UsageLimits(request_limit=5, total_tokens_limit=2000)
    ) -> None:
        self.usage_limits: UsageLimits = usage_limits

        self.generation_agent: Agent[PromptPayload, LocatorSuggestionsResponse] = (
            Agent[PromptPayload, LocatorSuggestionsResponse](
            model=get_model(llm_provider=llm_provider),
            system_prompt=(
                "You are an expert for healing broken robotframework locator.\n"
                "You compare the locator in the 'robot_code_line' to the 'html_ids' found "
                " and make **3** suggestions to fix the broken locator found in 'error_msg'.\n"
                "Input: a dict with keys `robot_code_line`, `html_ids` and 'error_msg'.  \n"
                "Example Output: **only** valid JSON matching this schema:\n"
                "```\n"
                "{\n"
                '  "suggestions": ["example_locator1", "example_locator2"]\n'
                "}\n"
                "```\n"
                "Do not emit any commentary, markdown or surrounding text."
            ),
            deps_type=PromptPayload,
            output_type=LocatorSuggestionsResponse
        ))

    async def heal_async(self, ctx: RunContext[PromptPayload]) -> List[str]:
        """Generates suggestions for fixing broken locator.

        Args:
            ctx (RunContext): PydanticAI context.

        Returns:
            (List): Suggestions for fixed locators.
        """
        gen_resp: AgentRunResult = await self.generation_agent.run(
            "Heal the broken locator found in the error message.",
            deps=ctx.deps,
            usage_limits=self.usage_limits
        )
        return gen_resp.output.suggestions
