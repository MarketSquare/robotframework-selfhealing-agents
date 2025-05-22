from typing import Optional
from robot.libraries.BuiltIn import BuiltIn

class RobotDomUtils:
    """
    A utility class to operate on the DOM of a web page.
    It provides methods to check, extract and manipulate HTML elements.
    """

    def __init__(self, library_instance: Optional[object] = None):      #ToDo: Investigate type hint for library_instance
        """
        Initializes the RobotDomUtils class.

        Args:
            library_instance: An instance of the Robot Framework library to interact with.
        """
        self.library_instance = library_instance or BuiltIn().get_library_instance('Browser')

    def is_locator_unique(self, locator: str) -> bool:
        """
        Checks if the given locator is unique in the DOM.

        Args:
            locator (str): The locator to check.

        Returns:
            bool: True if the locator is unique, False otherwise.
        """
        return self.library_instance.get_element_count(locator) == 1
    
    def is_locator_visible(self, locator: str) -> bool:
        """
        Checks if the given locator is visible in the DOM.

        Args:
            locator (str): The locator to check.

        Returns:
            bool: True if the locator is visible, False otherwise.
        """
        return 'visible' in self.library_instance.get_element_states(locator)
