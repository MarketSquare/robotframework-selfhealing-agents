from typing import Optional

from bs4 import BeautifulSoup
from robot.libraries.BuiltIn import BuiltIn

from RobotAid.self_healing_system.context_retrieving.base_dom_utils import BaseDomUtils
from RobotAid.self_healing_system.context_retrieving.dom_soap_utils import SoupDomUtils


class SeleniumDomUtils(BaseDomUtils):
    """Selenium library specific DOM utility implementation.

    This class provides DOM interaction methods specific to the Robot Framework
    SeleniumLibrary.
    """

    def __init__(self, library_instance: Optional[object] = None):
        """Initialize Selenium DOM utilities.

        Args:
            library_instance: An instance of the SeleniumLibrary.
        """
        if library_instance is None:
            try:
                library_instance = BuiltIn().get_library_instance("SeleniumLibrary")
            except Exception:
                print(
                    "SeleniumLibrary is not available. Selenium DOM utility will be limited."
                )
                library_instance = None

        super().__init__(library_instance)

    def is_locator_valid(self, locator: str) -> bool:
        """Check if the locator is valid using Selenium library methods.

        Args:
            locator: The locator to check.

        Returns:
            True if the locator is valid, False otherwise.
        """
        if self.library_instance is None:
            return True
        try:
            # Use dynamic attribute access to handle different SeleniumLibrary versions
            getattr(self.library_instance, "get_webelement")(locator)
            return True
        except Exception:
            return False

    def is_locator_unique(self, locator: str) -> bool:
        """Check if the locator is unique using Selenium library methods.

        Args:
            locator: The locator to check.

        Returns:
            True if the locator is unique, False otherwise.
        """
        if self.library_instance is None:
            return True  # Skip validation if library is not available

        try:
            # Use dynamic attribute access to handle different SeleniumLibrary versions
            elements = getattr(self.library_instance, "get_webelements")(locator)
            return len(elements) == 1
        except Exception:
            return False

    def is_locator_visible(self, locator: str) -> bool:
        """Check if the locator is visible using Selenium library methods.

        Args:
            locator: The locator to check.

        Returns:
            True if the locator is visible, False otherwise.
        """
        if self.library_instance is None:
            return True  # Skip validation if library is not available

        try:
            # Use dynamic attribute access for element visibility check
            getattr(self.library_instance, "element_should_be_visible")(locator)
            return True
        except Exception:
            return False

    def get_dom_tree(self) -> str:
        """Retrieve the DOM tree using Selenium library methods.

        Returns:
            str: The DOM tree as a string.
        """
        if self.library_instance is None:
            return "<html><body>SeleniumLibrary not available</body></html>"

        try:
            page_source = getattr(self.library_instance, "get_source")()

            soup: BeautifulSoup = BeautifulSoup(page_source, "html.parser")
            source: str = SoupDomUtils().get_simplified_dom_tree(
                str(soup.body) if soup.body else str(soup)
            )
            return source

        except Exception as e:
            return f"<html><body>Error retrieving DOM tree: {str(e)}</body></html>"

    def get_library_type(self) -> str:
        """Get the library type identifier.

        Returns:
            str: The library type identifier.
        """
        return "selenium"

    def is_element_clickable(self, locator: str) -> bool:
        """Check if the element is clickable using Selenium library methods.

        Args:
            locator: The locator to check.

        Returns:
            True if the element is clickable, False otherwise.
        """
        if self.library_instance is None:
            return False
        try:
            element = getattr(self.library_instance, "get_webelement")(locator)

            # Get tag name using element property
            tag = element.tag_name.lower()

            # Check basic clickable tags
            if tag == "button" or tag == "a":
                return True
            elif tag == "input":
                # Check input type for clickable input elements
                input_type = getattr(self.library_instance, "execute_javascript")(
                    "return arguments[0].type;", "ARGUMENTS", element
                )
                if input_type in [
                    "button",
                    "radio",
                    "checkbox",
                    "search",
                    "reset",
                    "submit",
                ]:
                    return True

            # Check for custom/framework-specific clickable elements
            other_clickable_tags = [
                "mat-button",  # Angular Material
                "mat-radio-button",
                "mat-checkbox",
                "md-button",  # Older Angular Material
                "ion-button",  # Ionic
                "vaadin-button",  # Vaadin
                "paper-button",  # Polymer
                "x-button",  # Generic custom button
                "select",
                "textarea",
            ]

            if tag in other_clickable_tags:
                return True

            # Check cursor style as final indicator
            cursor_style = getattr(self.library_instance, "execute_javascript")(
                "return window.getComputedStyle(arguments[0]).getPropertyValue('cursor');",
                "ARGUMENTS",
                element,
            )
            if cursor_style == "pointer":
                return True

            return False
        except Exception:
            return False
