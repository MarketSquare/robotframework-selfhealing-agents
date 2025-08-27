from typing import Final, Mapping, Type

from SelfhealingAgents.utils.cfg import Cfg
from SelfhealingAgents.self_healing_system.agents.locator_agent.base_locator_agent import BaseLocatorAgent
from SelfhealingAgents.self_healing_system.agents.locator_agent.browser_locator_agent import BrowserLocatorAgent
from SelfhealingAgents.self_healing_system.agents.locator_agent.selenium_locator_agent import SeleniumLocatorAgent
from SelfhealingAgents.self_healing_system.context_retrieving.library_dom_utils.base_dom_utils import BaseDomUtils


_AGENT_MAPPING: Final[Mapping[str, Type[BaseLocatorAgent]]] = {
    "browser": BrowserLocatorAgent,
    "selenium": SeleniumLocatorAgent,
    # "appium": AppiumLocatorAgent      # Not yet implemented
}


class LocatorAgentFactory:
    """Factory class for creating locator agents at runtime.

    Provides a clean way to create different flavors of locator agents
    based on the automation library being used. The decision about which agent to
    create is made at runtime based on the provided agent type.
    """
    @staticmethod
    def create_agent(
        agent_type: str,
        cfg: Cfg,
        dom_utility: BaseDomUtils,
    ) -> BaseLocatorAgent:
        """Creates a locator agent of the specified type.

        Args:
            agent_type (str): The type of agent to create (e.g., 'browser', 'selenium').
            cfg (Cfg): Instance of Cfg config class containing user-defined app configuration.
            dom_utility (BaseDomUtils): DOM utility instance for the agent.

        Returns:
            BaseLocatorAgent: An instance of the requested locator agent type.

        Raises:
            ValueError: If the agent type is not supported.
        """
        agent: Type[BaseLocatorAgent] = _AGENT_MAPPING.get(agent_type)
        if agent is None:
            supported: str = ", ".join(sorted(_AGENT_MAPPING.keys()))
            raise ValueError(f"Unsupported agent type: {agent}. Supported types: {supported}")
        return agent(cfg=cfg, dom_utility=dom_utility)
