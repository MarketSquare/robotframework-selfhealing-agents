from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.usage import UsageLimits

from RobotAid.utils.cfg import Cfg
from RobotAid.self_healing_system.agents.prompts.orchestrator.prompts_orchestrator import PromptsOrchestrator
from RobotAid.self_healing_system.llm.client_model import get_client_model
from RobotAid.self_healing_system.schemas.internal_state.prompt_payload import PromptPayload
from RobotAid.self_healing_system.schemas.api.locator_healing import (
    LocatorHealingResponse,
    NoHealingNeededResponse,
)
from RobotAid.self_healing_system.agents.locator_agent.base_locator_agent import BaseLocatorAgent


class OrchestratorAgent:
    """Routes raw failure text to the appropriate healing tool.

    Attributes:
        cfg: Instance of Cfg config class containing user defined app configuration.
        locator_agent: LocatorAgent instance.
    """

    def __init__(
        self,
        cfg: Cfg,
        locator_agent: BaseLocatorAgent,
        usage_limits: UsageLimits = UsageLimits(
            request_limit=5, total_tokens_limit=2000
        ),
    ) -> None:
        """Initialize the OrchestratorAgent.

        Args:
            cfg: Instance of Cfg config class containing user defined app configuration.
            locator_agent: LocatorAgent instance for handling locator healing.
            usage_limits: Token and request limits for the agent. Defaults to
                UsageLimits with request_limit=5 and total_tokens_limit=2000.
        """
        self.locator_agent: BaseLocatorAgent = locator_agent
        self.usage_limits: UsageLimits = usage_limits
        self.agent: Agent[PromptPayload, str] = Agent[PromptPayload, str](
            model=get_client_model(
                provider=cfg.orchestrator_agent_provider,
                model=cfg.orchestrator_agent_model,
                cfg=cfg,
            ),
            system_prompt=PromptsOrchestrator.get_system_msg(),
            deps_type=PromptPayload,
            output_type=[self._get_healed_locators, str],
        )

    async def run_async(
        self, robot_ctx_payload: PromptPayload
    ) -> str | LocatorHealingResponse | NoHealingNeededResponse:
        """Run orchestration asynchronously.

        Args:
            robot_ctx_payload: Contains context for the self-healing process of the LLM.

        Returns:
            List of repaired locator suggestions.
        """
        if not self.locator_agent.is_failed_locator_error(robot_ctx_payload.error_msg):
            return NoHealingNeededResponse(message=robot_ctx_payload.error_msg)

        response: AgentRunResult = await self.agent.run(
            PromptsOrchestrator.get_user_msg(robot_ctx_payload),
            deps=robot_ctx_payload,
            usage_limits=self.usage_limits,
            model_settings={"temperature": 0.1, "parallel_tool_calls": False},
        )
        return response.output

    async def _get_healed_locators(self, ctx: RunContext[PromptPayload]) -> str:
        """Get a list of healed locator suggestions for a broken locator.

        Args:
            ctx: PydanticAI tool context.

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