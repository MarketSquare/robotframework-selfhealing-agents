from enum import Enum
from typing import Optional, Union


from RobotAid.self_healing_system.context_retrieving.frameworks.appium_dom_utils import (
    AppiumDomUtils,
)
from RobotAid.self_healing_system.context_retrieving.frameworks.base_dom_utils import BaseDomUtils
from RobotAid.self_healing_system.context_retrieving.frameworks.browser_dom_utils import (
    BrowserDomUtils,
)
from RobotAid.self_healing_system.context_retrieving.frameworks.selenium_dom_utils import (
    SeleniumDomUtils,
)


class DomUtilityType(Enum):
    """Enumeration of supported DOM utility types."""

    BROWSER = "browser"
    SELENIUM = "selenium"
    APPIUM = "appium"


class DomUtilityFactory:
    """Factory class for creating library-specific DOM utilities.

    This factory provides a centralized way to create the appropriate DOM utility
    instance based on the library type, making the system easily extensible for
    new Robot Framework libraries.
    """

    @staticmethod
    def create_dom_utility(
        utility_type: Optional[Union[DomUtilityType, str]] = None,
        library_instance: Optional[object] = None,
    ) -> BaseDomUtils:
        """Create a DOM utility instance based on the specified type.

        Args:
            utility_type: The type of DOM utility to create. Can be a DomUtilityType enum,
                         a string ('browser', 'selenium', 'appium'), or None for auto-detection.
            library_instance: Optional library instance to use. If not provided,
                             the factory will attempt to get it automatically.

        Returns:
            BaseDomUtils: An instance of the appropriate DOM utility class.

        Raises:
            ValueError: If the utility type is not supported.
        """

        # Convert string to enum if necessary
        if isinstance(utility_type, str):
            try:
                utility_type = DomUtilityType(utility_type.lower())
            except ValueError:
                raise ValueError(f"Unsupported DOM utility type: {utility_type}")
        if utility_type == DomUtilityType.BROWSER:
            return BrowserDomUtils(library_instance)
        elif utility_type == DomUtilityType.SELENIUM:
            return SeleniumDomUtils(library_instance)
        elif utility_type == DomUtilityType.APPIUM:
            return AppiumDomUtils(library_instance)
        else:
            raise ValueError(f"Unsupported DOM utility type: {utility_type}")

    @staticmethod
    def create_dom_utility_from_agent_type(
        agent_type: str, library_instance: Optional[object] = None
    ) -> Optional[BaseDomUtils]:
        """Create a DOM utility instance based on agent type string.

        Args:
            agent_type: The agent type string (e.g., 'browser', 'selenium', 'appium').
            library_instance: Optional library instance to use.

        Returns:
            BaseDomUtils: An instance of the appropriate DOM utility class, or None if creation fails.
        """
        try:
            utility_type = DomUtilityType(agent_type.lower())
            return DomUtilityFactory.create_dom_utility(utility_type, library_instance)
        except (ValueError, Exception) as e:
            print(
                f"Warning: Could not create DOM utility for agent type '{agent_type}': {e}"
            )
            return None
