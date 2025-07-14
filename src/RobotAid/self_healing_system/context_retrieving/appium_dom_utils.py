from typing import Optional

from robot.libraries.BuiltIn import BuiltIn

from RobotAid.self_healing_system.context_retrieving.base_dom_utils import BaseDomUtils


class AppiumDomUtils(BaseDomUtils):
    """Appium library specific DOM utility implementation.

    This class provides DOM interaction methods specific to the Robot Framework
    AppiumLibrary for mobile application testing.
    """

    def __init__(self, library_instance: Optional[object] = None):
        """Initialize Appium DOM utilities.

        Args:
            library_instance: An instance of the AppiumLibrary.
        """
        if library_instance is None:
            try:
                library_instance = BuiltIn().get_library_instance("AppiumLibrary")
            except Exception:
                print(
                    "AppiumLibrary is not available. Appium DOM utility will be limited."
                )
                library_instance = None

        super().__init__(library_instance)

    def is_locator_valid(self, locator: str) -> bool:
        """Check if the locator is valid using Appium library methods.

        Args:
            locator (str): The locator to check.

        Returns:
            bool: True if the locator is valid, False otherwise.
        """
        if self.library_instance is None:
            return True
        try:
            # Use dynamic attribute access to handle different AppiumLibrary versions
            if hasattr(self.library_instance, "get_webelements"):
                elements = getattr(self.library_instance, "get_webelements")(locator)
            else:
                return True  # Default to valid if method not found
            return len(elements) > 0
        except Exception:
            return False

    def is_locator_unique(self, locator: str) -> bool:
        """Check if the locator is unique using Appium library methods.

        Args:
            locator (str): The locator to check.

        Returns:
            bool: True if the locator is unique, False otherwise.
        """
        if self.library_instance is None:
            return True  # Skip validation if library is not available

        try:
            # Use dynamic attribute access to handle different AppiumLibrary versions
            if hasattr(self.library_instance, "get_webelements"):
                elements = getattr(self.library_instance, "get_webelements")(locator)
            else:
                return True  # Default to valid if method not found
            return len(elements) == 1
        except Exception:
            return False

    def is_locator_visible(self, locator: str) -> bool:
        """Check if the locator is visible using Appium library methods.

        Args:
            locator (str): The locator to check.

        Returns:
            bool: True if the locator is visible, False otherwise.
        """
        if self.library_instance is None:
            return True  # Skip validation if library is not available

        try:
            # Use dynamic attribute access for element visibility check
            if hasattr(self.library_instance, "element_should_be_visible"):
                # Try the should be visible method and catch exceptions
                try:
                    getattr(self.library_instance, "element_should_be_visible")(locator)
                    return True
                except Exception:
                    return False
            else:
                return True  # Default to visible if method not found
        except Exception:
            return False

    def get_dom_tree(self) -> str:
        """Retrieve the DOM tree using Appium library methods.

        Note: For mobile applications, this returns the page source which
        contains the UI hierarchy in XML format.

        Returns:
            str: The DOM/UI tree as a string.
        """
        if self.library_instance is None:
            return "<hierarchy>AppiumLibrary not available</hierarchy>"

        try:
            if hasattr(self.library_instance, "get_source"):
                page_source = getattr(self.library_instance, "get_source")()
            elif hasattr(self.library_instance, "get_page_source"):
                page_source = getattr(self.library_instance, "get_page_source")()
            else:
                # Try to get the driver and get page source directly
                driver = getattr(self.library_instance, "_current_application", None)
                if driver:
                    page_source = driver.page_source
                else:
                    return "<hierarchy>Unable to retrieve page source</hierarchy>"

            # For mobile apps, we return the raw XML as it's already structured
            return page_source

        except Exception as e:
            return f"<hierarchy>Error retrieving DOM tree: {str(e)}</hierarchy>"

    def get_library_type(self) -> str:
        """Get the library type identifier.

        Returns:
            str: The library type identifier.
        """
        return "appium"
