"""Orchestrator agent using Programmatic Hand-Off pattern.

Refactored for ADR-001d: The orchestrator no longer makes LLM calls.
It uses deterministic routing via is_failed_locator_error() and
delegates directly to the locator agent.
"""
from pydantic_ai.usage import RunUsage, UsageLimits
from robot.api import logger as rf_logger

from SelfhealingAgents.self_healing_system.agents.locator_agent.base_locator_agent import (
    BaseLocatorAgent,
)
from SelfhealingAgents.self_healing_system.schemas.api.locator_healing import (
    LocatorHealingResponse,
    NoHealingNeededResponse,
)
from SelfhealingAgents.self_healing_system.schemas.internal_state.prompt_payload import (
    PromptPayload,
)
from SelfhealingAgents.utils.cfg import Cfg
from SelfhealingAgents.utils.logging import log


class OrchestratorAgent:
    """Routes failure payloads to the appropriate healing agent.

    Uses Programmatic Hand-Off (not LLM-based Agent Delegation) because routing
    is deterministic: is_failed_locator_error() decides which path to take.

    Attributes:
        _cfg (Cfg): Application configuration.
        _locator_agent (BaseLocatorAgent): Agent for locator healing.
        _usage_limits (UsageLimits): Token and request limits for child agents.
    """

    def __init__(
        self,
        cfg: Cfg,
        locator_agent: BaseLocatorAgent,
    ) -> None:
        """Initializes the OrchestratorAgent.

        Args:
            cfg: Application configuration. The orchestrator_agent_provider and
                 orchestrator_agent_model fields are preserved for backward
                 compatibility but are no longer used for LLM calls.
            locator_agent: LocatorAgent instance for handling locator healing.
        """
        self._cfg = cfg
        self._locator_agent: BaseLocatorAgent = locator_agent
        self._usage_limits: UsageLimits = UsageLimits(
            request_limit=cfg.request_limit,
            total_tokens_limit=cfg.total_tokens_limit,
        )

    @log
    async def run_async(
        self, robot_ctx_payload: PromptPayload
    ) -> LocatorHealingResponse | NoHealingNeededResponse:
        """Runs deterministic routing and delegates to the appropriate agent.

        Programmatic Hand-Off pattern: application code decides routing,
        not an LLM. The is_failed_locator_error() check is the routing
        decision.

        Args:
            robot_ctx_payload: Context for the self-healing process.

        Returns:
            LocatorHealingResponse with healing suggestions, or
            NoHealingNeededResponse if the error is not a locator error.
        """
        # Shared usage tracker for all agent calls in this healing flow
        usage = RunUsage()

        # --- Deterministic routing (no LLM needed) ---
        if not self._locator_agent.is_failed_locator_error(
            robot_ctx_payload.error_msg
        ):
            return NoHealingNeededResponse(message=robot_ctx_payload.error_msg)

        # --- Programmatic Hand-Off to locator agent ---
        result = await self._locator_agent.heal_async(
            robot_ctx_payload,
            usage=usage,
            usage_limits=self._usage_limits,
        )

        rf_logger.info(
            f"Healing complete. Total tokens: {usage.total_tokens}",
            also_console=True,
        )

        return result
