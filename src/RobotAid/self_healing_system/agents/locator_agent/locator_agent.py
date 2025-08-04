from typing import Optional, Union

from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits

from RobotAid.utils.cfg import Cfg
from RobotAid.self_healing_system.agents.locator_agent.base_locator_agent import BaseLocatorAgent
from RobotAid.self_healing_system.agents.locator_agent.locator_agent_factory import (
    LocatorAgentFactory,
    LocatorAgentType,
)
from RobotAid.self_healing_system.schemas.internal_state.prompt_payload import PromptPayload


class LocatorAgent:
    """Legacy LocatorAgent class for backward compatibility.

    This class maintains backward compatibility while providing access to the new
    agent flavor system. It automatically detects the appropriate agent type or
    allows explicit specification.

    For new code, consider using LocatorAgentFactory directly for better control
    over agent selection.

    Attributes:
        _agent: The underlying specific agent implementation.
        cfg: Instance of Cfg config class containing user defined app configuration.
        usage_limits: Usage token and request limits.
    """

    def __init__(
        self,
        cfg: Cfg,
        usage_limits: UsageLimits = UsageLimits(
            request_limit=5, total_tokens_limit=2000
        ),
        agent_type: Optional[Union[LocatorAgentType, str]] = None,
        dom_utility: Optional[object] = None,
    ) -> None:
        """Initialize the LocatorAgent.

        Args:
            cfg: Instance of Cfg config class containing user defined app configuration.
            usage_limits: Usage token and request limits.
            agent_type: Optional agent type. If None, will auto-detect based on available libraries.
            dom_utility: Optional DOM utility instance for the specific library.
        """
        self.cfg = cfg
        self.usage_limits = usage_limits

        if agent_type is None:
            # Auto-detect agent type for backward compatibility
            self._agent = LocatorAgentFactory.create_auto_detected_agent(
                cfg=cfg,
                usage_limits=usage_limits,
                dom_utility=dom_utility,
            )
        else:
            self._agent = LocatorAgentFactory.create_agent(
                agent_type=agent_type,
                cfg=cfg,
                usage_limits=usage_limits,
                dom_utility=dom_utility,
            )

    async def heal_async(self, ctx: RunContext[PromptPayload]) -> str:
        """Generates suggestions for fixing broken locator.

        Args:
            ctx: PydanticAI context.

        Returns:
            List of repaired locator suggestions.
        """
        return await self._agent.heal_async(ctx)

    @property
    def generation_agent(self) -> Agent[PromptPayload, str]:
        """Get the underlying generation agent for compatibility.

        Returns:
            The underlying PydanticAI agent.
        """
        return self._agent.generation_agent

    def get_agent_type(self) -> str:
        """Get the type of the underlying agent.

        Returns:
            The agent type identifier.
        """
        return self._agent.get_agent_type()

    def get_underlying_agent(self) -> BaseLocatorAgent:
        """Get the underlying specific agent implementation.

        Returns:
            The underlying agent implementation.
        """
        return self._agent

    def is_failed_locator_error(self, message: str) -> bool:
        """Check if the locator error is due to a failed locator.

        Args:
            message: The error message to check.

        Returns:
            True if the error is due to a failed locator, False otherwise.
        """
        return self._agent.is_failed_locator_error(message)
