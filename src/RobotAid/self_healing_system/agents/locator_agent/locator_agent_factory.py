from typing import Final, Mapping, Type

from RobotAid.utils.cfg import Cfg
from RobotAid.self_healing_system.agents.locator_agent.base_locator_agent import BaseLocatorAgent
from RobotAid.self_healing_system.agents.locator_agent.browser_locator_agent import BrowserLocatorAgent
from RobotAid.self_healing_system.agents.locator_agent.selenium_locator_agent import SeleniumLocatorAgent
from RobotAid.self_healing_system.context_retrieving.frameworks.base_dom_utils import BaseDomUtils


_AGENT_MAPPING: Final[Mapping[str, Type[BaseLocatorAgent]]] = {
    "browser": BrowserLocatorAgent,
    "selenium": SeleniumLocatorAgent,
    # "appium": AppiumLocatorAgent      # Not yet implemented
}


class LocatorAgentFactory:
    """Factory class for creating locator agents at runtime.

    This factory provides a clean way to create different flavors of locator agents
    based on the automation library being used. The decision about which agent to
    create is made at runtime based on the provided agent type.
    """

    @staticmethod
    def create_agent(
        agent_type: str,
        cfg: Cfg,
        dom_utility: BaseDomUtils,
    ) -> BaseLocatorAgent:
        """Create a locator agent of the specified type.

        Args:
            agent_type: The type of agent to create (browser, selenium, or appium).
                       Can be LocatorAgentType enum, DomUtilityType enum, or string.
            cfg: Instance of Cfg config class containing user defined app configuration.
            dom_utility: Optional DOM utility instance. If not provided, will be created
                        automatically based on agent type.

        Returns:
            An instance of the requested locator agent type.

        Raises:
            ValueError: If the agent type is not supported.
        """
        agent = _AGENT_MAPPING.get(agent_type)
        if agent is None:
            supported = ", ".join(sorted(_AGENT_MAPPING.keys()))
            raise ValueError(f"Unsupported agent type: {agent_type}. Supported types: {supported}")
        return agent(cfg=cfg, dom_utility=dom_utility)
