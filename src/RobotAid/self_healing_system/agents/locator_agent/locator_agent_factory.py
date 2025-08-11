from enum import Enum
from typing import Optional, Union

from pydantic_ai.usage import UsageLimits

from RobotAid.utils.cfg import Cfg
from RobotAid.self_healing_system.agents.locator_agent.base_locator_agent import BaseLocatorAgent
from RobotAid.self_healing_system.agents.locator_agent.browser_locator_agent import (
    BrowserLocatorAgent,
)
from RobotAid.self_healing_system.agents.locator_agent.selenium_locator_agent import (
    SeleniumLocatorAgent,
)
from RobotAid.self_healing_system.context_retrieving.frameworks.base_dom_utils import BaseDomUtils
from RobotAid.self_healing_system.context_retrieving.dom_utils.dom_utility_factory import DomUtilityType


class LocatorAgentType(Enum):
    """Enumeration of supported locator agent types."""

    BROWSER = "browser"
    SELENIUM = "selenium"
    APPIUM = "appium"  # Placeholder for future Appium support


class LocatorAgentFactory:
    """Factory class for creating locator agents at runtime.

    This factory provides a clean way to create different flavors of locator agents
    based on the automation library being used. The decision about which agent to
    create is made at runtime based on the provided agent type.
    """

    @staticmethod
    def create_agent(
        agent_type: Union[LocatorAgentType, str, DomUtilityType],
        cfg: Cfg,
        usage_limits: Optional[UsageLimits] = None,
        dom_utility: Optional[BaseDomUtils] = None,
    ) -> BaseLocatorAgent:
        """Create a locator agent of the specified type.

        Args:
            agent_type: The type of agent to create (browser, selenium, or appium).
                       Can be LocatorAgentType enum, DomUtilityType enum, or string.
            cfg: Instance of Cfg config class containing user defined app configuration.
            usage_limits: Optional usage limits for the agent.
            dom_utility: Optional DOM utility instance. If not provided, will be created
                        automatically based on agent type.

        Returns:
            An instance of the requested locator agent type.

        Raises:
            ValueError: If the agent type is not supported.
        """
        if usage_limits is None:
            usage_limits = UsageLimits(request_limit=5, total_tokens_limit=2000)

        # Normalize agent type to enum
        agent_type = LocatorAgentFactory._normalize_agent_type(agent_type)
        if agent_type == LocatorAgentType.BROWSER:
            return BrowserLocatorAgent(
                cfg=cfg,
                usage_limits=usage_limits,
                dom_utility=dom_utility,
            )
        elif agent_type == LocatorAgentType.SELENIUM:
            return SeleniumLocatorAgent(
                cfg=cfg,
                usage_limits=usage_limits,
                dom_utility=dom_utility,
            )
        else:
            # For now, APPIUM is not implemented, but we can add it easily
            raise ValueError(
                f"Unsupported agent type: {agent_type}. Supported types:"
                f" {[t.value for t in LocatorAgentType if t != LocatorAgentType.APPIUM]}"
            )

    @staticmethod
    def _normalize_agent_type(
        agent_type: Union[LocatorAgentType, str, DomUtilityType],
    ) -> LocatorAgentType:
        """Normalize different agent type representations to LocatorAgentType enum.

        Args:
            agent_type: The agent type to normalize.

        Returns:
            The normalized agent type.

        Raises:
            ValueError: If the agent type cannot be normalized.
        """
        if isinstance(agent_type, LocatorAgentType):
            return agent_type
        elif isinstance(agent_type, DomUtilityType):
            # Convert DomUtilityType to LocatorAgentType
            return LocatorAgentType(agent_type.value)
        elif isinstance(agent_type, str):
            try:
                return LocatorAgentType(agent_type.lower())
            except ValueError:
                raise ValueError(
                    f"Unsupported agent type string: {agent_type}. Supported types: {[t.value for t in LocatorAgentType]}"
                )
        else:
            raise ValueError(f"Unsupported agent type: {type(agent_type)}")
