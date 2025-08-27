from typing import Final, Mapping, Type

from SelfhealingAgents.self_healing_system.context_retrieving.library_dom_utils.base_dom_utils import BaseDomUtils
from SelfhealingAgents.self_healing_system.context_retrieving.library_dom_utils.appium_dom_utils import (
    AppiumDomUtils,
)
from SelfhealingAgents.self_healing_system.context_retrieving.library_dom_utils.browser_dom_utils import (
    BrowserDomUtils,
)
from SelfhealingAgents.self_healing_system.context_retrieving.library_dom_utils.selenium_dom_utils import (
    SeleniumDomUtils,
)


_DOM_UTILITY_TYPE: Final[Mapping[str, Type[BaseDomUtils]]] = {
    "browser": BrowserDomUtils,
    "selenium": SeleniumDomUtils,
    "appium": AppiumDomUtils
}


class DomUtilityFactory:
    """Factory for creating library-specific DOM utility instances.

    Provides a centralized way to instantiate the appropriate DOM utility
    based on the library type (e.g., 'browser', 'selenium', 'appium').
    """
    @staticmethod
    def create_dom_utility(agent_type: str) -> BaseDomUtils:
        """Creates a DOM utility instance based on the specified type.

        Args:
            agent_type (str): The type of DOM utility to create. Should be one of
                'browser', 'selenium', or 'appium'.

        Returns:
            BaseDomUtils: An instance of the appropriate DOM utility class.

        Raises:
            ValueError: If the utility type is not supported.
        """
        dom_utility: Type[BaseDomUtils] = _DOM_UTILITY_TYPE.get(agent_type)
        if dom_utility is None:
            raise ValueError(f"Unsupported DOM utility type: {dom_utility}")
        return dom_utility()