from typing import Optional, Union
from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits

from RobotAid.self_healing_system.agents.base_locator_agent import BaseLocatorAgent
from RobotAid.self_healing_system.agents.locator_agent_factory import (
    LocatorAgentFactory,
    LocatorAgentType,
)
from RobotAid.self_healing_system.schemas import PromptPayload
from RobotAid.utils.app_settings import AppSettings
from RobotAid.utils.client_settings import ClientSettings


class LocatorAgent:
    """Legacy LocatorAgent class for backward compatibility.

    This class maintains backward compatibility while providing access to the new
    agent flavor system. It automatically detects the appropriate agent type or
    allows explicit specification.

    For new code, consider using LocatorAgentFactory directly for better control
    over agent selection.

    Attributes:
        _agent (BaseLocatorAgent): The underlying specific agent implementation.
        app_settings (AppSettings): Instance of AppSettings containing user defined app configuration.
        client_settings (ClientSettings): Instance of ClientSettings containing user defined client configuration.
        usage_limits (UsageLimits): Usage token and request limits.
    """

    def __init__(
        self,
        app_settings: AppSettings,
        client_settings: ClientSettings,
        usage_limits: UsageLimits = UsageLimits(
            request_limit=5, total_tokens_limit=2000
        ),
        agent_type: Optional[Union[LocatorAgentType, str]] = None,
        dom_utility: Optional[object] = None,
    ) -> None:
        """Initialize the LocatorAgent.

        Args:
            app_settings: Instance of AppSettings containing user defined app configuration.
            client_settings: Instance of ClientSettings containing user defined client configuration.
            usage_limits: Usage token and request limits.
            agent_type: Optional agent type. If None, will auto-detect based on available libraries.
            dom_utility: Optional DOM utility instance for the specific library.
        """
        self.app_settings = app_settings
        self.client_settings = client_settings
        self.usage_limits = usage_limits

        if agent_type is None:
            # Auto-detect agent type for backward compatibility
            self._agent = LocatorAgentFactory.create_auto_detected_agent(
                app_settings=app_settings,
                client_settings=client_settings,
                usage_limits=usage_limits,
                dom_utility=dom_utility,
            )
        else:
            self._agent = LocatorAgentFactory.create_agent(
                agent_type=agent_type,
                app_settings=app_settings,
                client_settings=client_settings,
                usage_limits=usage_limits,
                dom_utility=dom_utility,
            )

    async def heal_async(self, ctx: RunContext[PromptPayload]) -> str:
        """Generates suggestions for fixing broken locator.

        Args:
            ctx (RunContext): PydanticAI context.

        Returns:
            (str): List of repaired locator suggestions.
        """
        return await self._agent.heal_async(ctx)

    @property
    def generation_agent(self) -> Agent[PromptPayload, str]:
        """Get the underlying generation agent for compatibility.

        Returns:
            Agent[PromptPayload, str]: The underlying PydanticAI agent.
        """
        return self._agent.generation_agent

    def get_agent_type(self) -> str:
        """Get the type of the underlying agent.

        Returns:
            str: The agent type identifier.
        """
        return self._agent.get_agent_type()

    def get_underlying_agent(self) -> BaseLocatorAgent:
        """Get the underlying specific agent implementation.

        Returns:
            BaseLocatorAgent: The underlying agent implementation.
        """
        return self._agent
