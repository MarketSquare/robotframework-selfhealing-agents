from typing import Final, Mapping, Type

from RobotAid.self_healing_system.context_retrieving.library_dom_utils.appium_dom_utils import (
    AppiumDomUtils,
)
from RobotAid.self_healing_system.context_retrieving.library_dom_utils.base_dom_utils import BaseDomUtils
from RobotAid.self_healing_system.context_retrieving.library_dom_utils.browser_dom_utils import (
    BrowserDomUtils,
)
from RobotAid.self_healing_system.context_retrieving.library_dom_utils.selenium_dom_utils import (
    SeleniumDomUtils,
)


_DOM_UTILITY_TYPE: Final[Mapping[str, Type[BaseDomUtils]]] = {
    "browser": BrowserDomUtils,
    "selenium": SeleniumDomUtils,
    "appium": AppiumDomUtils
}


class DomUtilityFactory:
    """Factory class for creating library-specific DOM utilities.

    This factory provides a centralized way to create the appropriate DOM utility
    instance based on the library type, making the system easily extensible for
    new Robot Framework library_dom_utils.
    """

    @staticmethod
    def create_dom_utility(agent_type: str) -> BaseDomUtils:
        """Create a DOM utility instance based on the specified type.

        Args:
            agent_type: The type of DOM utility to create. Can be a DomUtilityType enum,
                         a string ('browser', 'selenium', 'appium'), or None for auto-detection.

        Returns:
            BaseDomUtils: An instance of the appropriate DOM utility class.

        Raises:
            ValueError: If the utility type is not supported.
        """
        dom_utility = _DOM_UTILITY_TYPE.get(agent_type)
        if dom_utility is None:
            raise ValueError(f"Unsupported DOM utility type: {dom_utility}")
        return dom_utility()