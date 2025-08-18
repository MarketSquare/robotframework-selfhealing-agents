from robot.libraries.BuiltIn import BuiltIn

from RobotAid.utils.logging import log
from RobotAid.self_healing_system.context_retrieving.library_dom_utils.base_dom_utils import BaseDomUtils


class AppiumDomUtils(BaseDomUtils):
    """Appium library-specific DOM utility implementation.

    Provides DOM interaction methods tailored for Robot Framework's AppiumLibrary,
    including locator validation, uniqueness checks, DOM extraction, and locator metadata.

    Attributes:
        _library_instance: Instance of the AppiumLibrary used for DOM interactions.
    """
    def __init__(self):
        """Initializes AppiumDomUtils and retrieves the AppiumLibrary instance."""
        self._library_instance = BuiltIn().get_library_instance("AppiumLibrary")

    def is_locator_valid(self, locator: str) -> bool:
        """Checks if the locator is valid using AppiumLibrary methods.

        Args:
            locator (str): The locator to check.

        Returns:
            bool: True if the locator is valid, False otherwise.
        """
        if self._library_instance is None:
            return True
        try:
            # Use dynamic attribute access to handle different AppiumLibrary versions
            if hasattr(self._library_instance, "get_webelements"):
                elements = getattr(self._library_instance, "get_webelements")(locator)
            else:
                return True  # Default to valid if method not found
            return len(elements) > 0
        except Exception:
            return False

    def is_locator_unique(self, locator: str) -> bool:
        """Checks if the locator uniquely identifies a single element.

        Args:
            locator (str): The locator to check.

        Returns:
            bool: True if the locator is unique, False otherwise.
        """
        if self._library_instance is None:
            return True  # Skip validation if library is not available

        try:
            # Use dynamic attribute access to handle different AppiumLibrary versions
            if hasattr(self._library_instance, "get_webelements"):
                elements = getattr(self._library_instance, "get_webelements")(locator)
            else:
                return True  # Default to valid if method not found
            return len(elements) == 1
        except Exception:
            return False

    def get_dom_tree(self) -> str:
        """Retrieves the DOM tree using AppiumLibrary.

        For mobile applications, this returns the page source which contains the UI hierarchy in XML format.

        Returns:
            str: The DOM/UI tree as a string.
        """
        if self._library_instance is None:
            return "<hierarchy>AppiumLibrary not available</hierarchy>"

        try:
            if hasattr(self._library_instance, "get_source"):
                page_source = getattr(self._library_instance, "get_source")()
            elif hasattr(self._library_instance, "get_page_source"):
                page_source = getattr(self._library_instance, "get_page_source")()
            else:
                # Try to get the driver and get page source directly
                driver = getattr(self._library_instance, "_current_application", None)
                if driver:
                    page_source = driver.page_source
                else:
                    return "<hierarchy>Unable to retrieve page source</hierarchy>"

            # For mobile apps, we return the raw XML as it's already structured
            return page_source

        except Exception as e:
            return f"<hierarchy>Error retrieving DOM tree: {str(e)}</hierarchy>"

    def get_library_type(self) -> str:
        """Returns the library type identifier.

        Returns:
            str: The library type identifier ('appium').
        """
        return "appium"

    @log
    def get_locator_proposals(
        self, failed_locator: str, keyword_name: str
    ) -> list[str]:
        """Generates locator proposals for the given failed locator and keyword.

        Args:
            failed_locator (str): The locator that failed.
            keyword_name (str): The name of the keyword being executed.

        Returns:
            List[str]: A list of proposed locator strings.
        """
        pass

    def get_locator_metadata(self, locator: str) -> list[dict]:
        """Retrieves metadata for the element(s) matching the given locator.

        Args:
            locator (str): The locator to get metadata for.

        Returns:
            List[Dict]: A list of dictionaries containing metadata about the matched elements.
        """
        if self._library_instance is None:
            return []

        try:
            # Try to get elements using Appium library methods
            if hasattr(self._library_instance, "get_webelements"):
                elements = getattr(self._library_instance, "get_webelements")(locator)
            else:
                return []

            metadata_list = []

            for element in elements:
                metadata = {}

                # Get basic element properties for mobile elements
                try:
                    metadata["tag"] = (
                        element.tag_name.lower() if hasattr(element, "tag_name") else ""
                    )
                except Exception:
                    metadata["tag"] = ""

                try:
                    metadata["resource_id"] = element.get_attribute("resource-id") or ""
                except Exception:
                    metadata["resource_id"] = ""

                try:
                    metadata["class"] = element.get_attribute("class") or ""
                except Exception:
                    metadata["class"] = ""

                try:
                    metadata["text"] = element.text or ""
                except Exception:
                    metadata["text"] = ""

                try:
                    metadata["content_desc"] = (
                        element.get_attribute("content-desc") or ""
                    )
                except Exception:
                    metadata["content_desc"] = ""

                try:
                    metadata["name"] = element.get_attribute("name") or ""
                except Exception:
                    metadata["name"] = ""

                try:
                    metadata["value"] = element.get_attribute("value") or ""
                except Exception:
                    metadata["value"] = ""

                try:
                    metadata["package"] = element.get_attribute("package") or ""
                except Exception:
                    metadata["package"] = ""

                try:
                    metadata["checkable"] = element.get_attribute("checkable") == "true"
                except Exception:
                    metadata["checkable"] = False

                try:
                    metadata["checked"] = element.get_attribute("checked") == "true"
                except Exception:
                    metadata["checked"] = False

                try:
                    metadata["clickable"] = element.get_attribute("clickable") == "true"
                except Exception:
                    metadata["clickable"] = False

                try:
                    metadata["enabled"] = element.get_attribute("enabled") == "true"
                except Exception:
                    metadata["enabled"] = False

                try:
                    metadata["focusable"] = element.get_attribute("focusable") == "true"
                except Exception:
                    metadata["focusable"] = False

                try:
                    metadata["focused"] = element.get_attribute("focused") == "true"
                except Exception:
                    metadata["focused"] = False

                try:
                    metadata["scrollable"] = (
                        element.get_attribute("scrollable") == "true"
                    )
                except Exception:
                    metadata["scrollable"] = False

                try:
                    metadata["selected"] = element.get_attribute("selected") == "true"
                except Exception:
                    metadata["selected"] = False

                try:
                    metadata["displayed"] = element.get_attribute("displayed") == "true"
                except Exception:
                    metadata["displayed"] = False

                metadata_list.append(metadata)

            return metadata_list

        except Exception:
            return []
