from abc import ABC, abstractmethod
from typing import Optional


class BaseDomUtils(ABC):
    """Abstract base class for library-specific DOM utilities.

    This class defines the common interface that all DOM utility implementations
    must follow, ensuring consistency across different Robot Framework libraries.
    """

    def __init__(self, library_instance: Optional[object] = None):
        """Initialize the DOM utility with a library instance.

        Args:
            library_instance: An instance of the Robot Framework library.
        """
        self.library_instance = library_instance

    @abstractmethod
    def is_locator_valid(self, locator: str) -> bool:
        """Check if the given locator is valid in the DOM.

        Args:
            locator: The locator to check.

        Returns:
            True if the locator is valid, False otherwise.
        """
        pass

    @abstractmethod
    def is_locator_unique(self, locator: str) -> bool:
        """Check if the given locator is unique in the DOM.

        Args:
            locator: The locator to check.

        Returns:
            True if the locator is unique, False otherwise.
        """
        pass

    @abstractmethod
    def is_locator_visible(self, locator: str) -> bool:
        """Check if the given locator is visible in the DOM.

        Args:
            locator: The locator to check.

        Returns:
            True if the locator is visible, False otherwise.
        """
        pass

    @abstractmethod
    def get_dom_tree(self) -> str:
        """Retrieve the DOM tree of the current page.

        Returns:
            The DOM tree as a string.
        """
        pass

    @abstractmethod
    def get_library_type(self) -> str:
        """Get the library type identifier.

        Returns:
            The library type (e.g., 'browser', 'selenium', 'appium').
        """
        pass

    @abstractmethod
    def is_element_clickable(self, locator: str) -> bool:
        """Check if the element identified by the locator is clickable.

        Args:
            locator: The locator to check.

        Returns:
            True if the element is clickable, False otherwise.
        """
        pass

    @abstractmethod
    def get_locator_proposals(
        self, failed_locator: str, keyword_name: str
    ) -> list[str]:
        """Get proposals for the given locator.

        Args:
            locator: The locator to get proposals for.

        Returns:
            A list of proposed locators.
        """
        pass

    @abstractmethod
    def get_locator_metadata(self, locator: str) -> dict:
        """Get metadata for the given locator.

        Args:
            locator: The locator to get metadata for.

        Returns:
            A dictionary containing metadata about elements matching the locator.
            The dictionary may contain keys like 'tag', 'id', 'class', 'text', 'attributes', etc.
        """
        pass
