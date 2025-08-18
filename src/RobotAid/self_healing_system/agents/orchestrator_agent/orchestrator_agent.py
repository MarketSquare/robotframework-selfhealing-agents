from robot.api import logger
from pydantic_ai.usage import UsageLimits
from pydantic_ai.agent import AgentRunResult
from pydantic_ai import Agent, ModelRetry, RunContext

from RobotAid.utils.cfg import Cfg
from RobotAid.self_healing_system.llm.client_model import get_client_model
from RobotAid.self_healing_system.schemas.internal_state.prompt_payload import PromptPayload
from RobotAid.self_healing_system.agents.locator_agent.base_locator_agent import BaseLocatorAgent
from RobotAid.self_healing_system.agents.prompts.orchestrator.prompts_orchestrator import PromptsOrchestrator
from RobotAid.self_healing_system.schemas.api.locator_healing import (
    LocatorHealingResponse,
    NoHealingNeededResponse,
)


class OrchestratorAgent:
    """Routes raw failure text to the appropriate healing tool.

    Attributes:
        _cfg (Cfg): Instance of Cfg config class containing user-defined app configuration.
        _locator_agent (BaseLocatorAgent): LocatorAgent instance for handling locator healing.
        _usage_limits (UsageLimits): Usage limits for the orchestrator agent.
        _agent (Agent[PromptPayload, str]): The underlying agent for orchestrating healing.
    """
    def __init__(
        self,
        cfg: Cfg,
        locator_agent: BaseLocatorAgent,
    ) -> None:
        """Initializes the OrchestratorAgent.

        Args:
            cfg (Cfg): Instance of Cfg config class containing user-defined app configuration.
            locator_agent (BaseLocatorAgent): LocatorAgent instance for handling locator healing.
        """
        self._cfg = cfg
        self._locator_agent: BaseLocatorAgent = locator_agent
        self._usage_limits: UsageLimits = UsageLimits(cfg.request_limit, cfg.total_tokens_limit)
        self._agent: Agent[PromptPayload, str] = Agent[PromptPayload, str](
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
        """Runs orchestration asynchronously to provide locator healing suggestions.

        Args:
            robot_ctx_payload (PromptPayload): Contains context for the self-healing process of the LLM.

        Returns:
            str | LocatorHealingResponse | NoHealingNeededResponse: List of repaired locator suggestions
                                                                    or a message if no healing is needed.
        """
        if not self._locator_agent.is_failed_locator_error(robot_ctx_payload.error_msg):
            return NoHealingNeededResponse(message=robot_ctx_payload.error_msg)

        response: AgentRunResult = await self._agent.run(
            PromptsOrchestrator.get_user_msg(robot_ctx_payload),
            deps=robot_ctx_payload,
            usage_limits=self._usage_limits,
            model_settings={"temperature": 0.1, "parallel_tool_calls": False},
        )
        self._catch_token_limit_exceedance(response.output)
        return response.output

    async def _get_healed_locators(self, ctx: RunContext[PromptPayload]) -> str:
        """Gets a list of healed locator suggestions for a broken locator.

        Args:
            ctx (RunContext[PromptPayload]): PydanticAI tool context.

        Returns:
            str: List of repaired locator suggestions in JSON format.

        Raises:
            ModelRetry: If locator healing fails.

        Example:
            get_healed_locators(ctx, broken_locator="#btn-login")
            '{"suggestions": ["#btn-login-fixed", "input[type=\'submit\']", "css=.btn-login"]}'
        """
        try:
            return await self._locator_agent.heal_async(ctx)
        except Exception as e:
            raise ModelRetry(f"Locator healing failed: {str(e)}")

    @staticmethod
    def _catch_token_limit_exceedance(response_output: str) -> None:
        """Logs error in log.html of robot if token limit is exceeded.

        Args:
            response_output (str): The response from the LLM request.
        """
        if "error" in response_output:
            logger.info(response_output)