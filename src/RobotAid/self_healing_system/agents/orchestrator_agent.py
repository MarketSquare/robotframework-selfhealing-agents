from typing import List
from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.models.openai import OpenAIModel

from RobotAid.self_healing_system.clients.llm_client import get_model
from RobotAid.self_healing_system.agents.locator_agent import LocatorAgent
from RobotAid.self_healing_system.schemas import PromptPayload, LocatorHealingResponse


# MVP Orchestrator Agent - will be adjusted to context and when additional agents will be implemented.
class OrchestratorAgent:
    """Routes raw failure text to the appropriate healing tool.

    Attributes:
        locator_agent (LocatorAgent): LocatorAgent instance.
        llm_provider (str): Provider for LLM defined by user.
    """
    def __init__(self, locator_agent: LocatorAgent, llm_provider: str) -> None:
        self.locator_agent: LocatorAgent = locator_agent

        model: None | OpenAIModel | str = get_model(llm_provider)
        self.agent: Agent[PromptPayload, LocatorHealingResponse] = (
            Agent[PromptPayload, LocatorHealingResponse](
            model=model,
            system_prompt=(
                "Based on `error_msg` and `html_ids`, select and run the `locator_heal` tool."
                "You MUST call the tool. You are not allowed to create a response on your own."
            ),
            deps_type=PromptPayload,
            output_type=LocatorHealingResponse
        ))

        @self.agent.tool(name="locator_heal")
        async def locator_heal(ctx: RunContext[PromptPayload]) -> LocatorHealingResponse:
            """Invoke LocatorAgent on locator error.

            Args:
                ctx (RunContext): PydanticAI tool context.

            Returns:
                (LocatorHealingResponse): List of repaired locator suggestions.
            """
            suggestions: List[str] = await self.locator_agent.heal_async(ctx=ctx)
            return LocatorHealingResponse(suggestions=suggestions)

    async def run_async(self, robot_ctx: dict) -> LocatorHealingResponse:
        """Run orchestration asynchronously.

        Args:
            robot_ctx (dict): Contains context for the self-healing process of the LLM.

        Returns:
            (LocatorHealingResponse): List of repaired locators.
        """
        payload: PromptPayload = PromptPayload(**robot_ctx)
        result: AgentRunResult = await self.agent.run(
            payload.error_msg,
            deps=payload,
            usage_limits=UsageLimits(request_limit=5, total_tokens_limit=2000)
        )
        return result.output
