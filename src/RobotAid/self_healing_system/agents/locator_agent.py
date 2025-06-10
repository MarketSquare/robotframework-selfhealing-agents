from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits
from pydantic_ai.agent import AgentRunResult

from RobotAid.utils.app_settings import AppSettings
from RobotAid.utils.client_settings import ClientSettings
from RobotAid.self_healing_system.clients.llm_client import get_model
from RobotAid.self_healing_system.agents.prompts import PromptsLocator
from RobotAid.self_healing_system.schemas import PromptPayload, LocatorHealingResponse


# MVP LocatorAgent - prompt will be adjusted based on provided context.
class LocatorAgent:
    """Produces alternatives for broken locator.

    Attributes:
        app_settings (AppSettings): Instance of AppSettings containing user defined app configuration.
        client_settings (ClientSettings): Instance of ClientSettings containing user defined client configuration.
        usage_limits (UsageLimits): Usage token and request limits.
    """
    def __init__(
        self,
        app_settings: AppSettings,
        client_settings: ClientSettings,
        usage_limits: UsageLimits = UsageLimits(request_limit=5, total_tokens_limit=2000)
    ) -> None:
        self.usage_limits: UsageLimits = usage_limits

        self.generation_agent: Agent[PromptPayload, str] = (
            Agent[PromptPayload, str](
            model=get_model(provider=app_settings.locator_agent.provider,
                            model=app_settings.locator_agent.model,
                            client_settings=client_settings),
            system_prompt=PromptsLocator.system_msg,
            deps_type=PromptPayload,
            output_type=LocatorHealingResponse
        ))

    async def heal_async(self, ctx: RunContext[PromptPayload]) -> LocatorHealingResponse:
        """Generates suggestions for fixing broken locator.

        Args:
            ctx (RunContext): PydanticAI context.

        Returns:
            (LocatorHealingResponse): List of repaired locator suggestions.
        """
        response: AgentRunResult = await self.generation_agent.run(
            PromptsLocator.get_user_msg(ctx=ctx),
            deps=ctx.deps,
            usage_limits=self.usage_limits
        )
        return response.output
