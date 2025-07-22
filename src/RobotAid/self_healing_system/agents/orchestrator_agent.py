from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.usage import UsageLimits

from RobotAid.self_healing_system.agents.locator_agent import LocatorAgent
from RobotAid.self_healing_system.agents.prompts import PromptsOrchestrator
from RobotAid.self_healing_system.clients.llm_client import get_client_model
from RobotAid.self_healing_system.schemas import (
    LocatorHealingResponse,
    NoHealingNeededResponse,
    PromptPayload,
)
from RobotAid.utils.app_settings import AppSettings
from RobotAid.utils.client_settings import ClientSettings


# MVP Orchestrator Agent - will be adjusted to context and when additional agents will be implemented.
class OrchestratorAgent:
    """Routes raw failure text to the appropriate healing tool.

    Attributes:
        app_settings: Instance of AppSettings containing user defined app configuration.
        client_settings: Instance of ClientSettings containing user defined client configuration.
        locator_agent: LocatorAgent instance.
    """

    def __init__(
        self,
        app_settings: AppSettings,
        client_settings: ClientSettings,
        locator_agent: LocatorAgent,
        usage_limits: UsageLimits = UsageLimits(
            request_limit=5, total_tokens_limit=2000
        ),
    ) -> None:
        """Initialize the OrchestratorAgent.

        Args:
            app_settings: Application settings containing configuration.
            client_settings: Client settings for LLM connection.
            locator_agent: LocatorAgent instance for handling locator healing.
            usage_limits: Token and request limits for the agent. Defaults to
                UsageLimits with request_limit=5 and total_tokens_limit=2000.
        """
        self.locator_agent: LocatorAgent = locator_agent
        self.usage_limits: UsageLimits = usage_limits
        self.agent: Agent[PromptPayload, str] = Agent[PromptPayload, str](
            model=get_client_model(
                provider=app_settings.orchestrator_agent.provider,
                model=app_settings.orchestrator_agent.model,
                client_settings=client_settings,
            ),
            system_prompt=PromptsOrchestrator.system_msg,
            deps_type=PromptPayload,
            output_type=[self.get_healed_locators, str],
        )

    async def get_healed_locators(
        self, ctx: RunContext[PromptPayload], broken_locator: str
    ) -> str:
        """Get a list of healed locator suggestions for a broken locator.

        Args:
            ctx: PydanticAI tool context.
            broken_locator: Locator that needs to be healed.

        Returns:
            List of repaired locator suggestions in JSON format.

        Raises:
            ModelRetry: If locator healing fails.

        Example:
            get_healed_locators(ctx, broken_locator="#btn-login")
            '{"suggestions": ["#btn-login-fixed", "input[type=\'submit\']", "css=.btn-login"]}'
        """
        try:
            return await self.locator_agent.heal_async(ctx=ctx)
        except Exception as e:
            raise ModelRetry(f"Locator healing failed: {str(e)}")

    async def run_async(
        self, robot_ctx: dict
    ) -> str | LocatorHealingResponse | NoHealingNeededResponse:
        """Run orchestration asynchronously.

        Args:
            robot_ctx: Contains context for the self-healing process of the LLM.

        Returns:
            List of repaired locator suggestions.
        """
        payload: PromptPayload = PromptPayload(**robot_ctx)

        # Only run the agent in case of a locator error
        if not self.locator_agent.is_failed_locator_error(payload.error_msg):
            return NoHealingNeededResponse(message=payload.error_msg)

        response: AgentRunResult = await self.agent.run(
            PromptsOrchestrator.get_user_msg(payload),
            deps=payload,
            usage_limits=self.usage_limits,
            model_settings={"temperature": 0.1, "parallel_tool_calls": False},
        )
        return response.output
