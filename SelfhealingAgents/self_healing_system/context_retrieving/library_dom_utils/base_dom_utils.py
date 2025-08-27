from abc import ABC, abstractmethod


class BaseDomUtils(ABC):
    """Abstract base class for library-specific DOM utilities.

    Defines the common interface that all DOM utility implementations
    must follow, ensuring consistency across different Robot Framework DOM utilities.
    """
    @abstractmethod
    def __init__(self):
        """Initializes the DOM utility.

        This method should set up any required library-specific state.
        """
        pass

    @abstractmethod
    def is_locator_valid(self, locator: str) -> bool:
        """Checks if the given locator is valid in the DOM.

        Args:
            locator (str): The locator to check.

        Returns:
            bool: True if the locator is valid, False otherwise.
        """
        pass

    @abstractmethod
    def is_locator_unique(self, locator: str) -> bool:
        """Checks if the given locator is unique in the DOM.

        Args:
            locator (str): The locator to check.

        Returns:
            bool: True if the locator is unique, False otherwise.
        """
        pass

    @abstractmethod
    def get_dom_tree(self) -> str:
        """Retrieves the DOM tree of the current page.

        Returns:
            str: The DOM tree as a string.
        """
        pass

    @abstractmethod
    def get_library_type(self) -> str:
        """Gets the library type identifier.

        Returns:
            str: The library type (e.g., 'browser', 'selenium', 'appium').
        """
        pass

    @abstractmethod
    def is_element_clickable(self, locator: str) -> bool:
        """Checks if the element identified by the locator is clickable.

        Args:
            locator (str): The locator to check.

        Returns:
            bool: True if the element is clickable, False otherwise.
        """
        pass

    @abstractmethod
    def get_locator_proposals(
        self, failed_locator: str, keyword_name: str
    ) -> list[str]:
        """Gets proposals for the given locator.

        Args:
            failed_locator (str): The locator to get proposals for.
            keyword_name (str): The name of the keyword where the locator failed.

        Returns:
            list[str]: A list of proposed locators.
        """
        pass

    @abstractmethod
    def get_locator_metadata(self, locator: str) -> dict:
        """Gets metadata for the given locator.

        Args:
            locator (str): The locator to get metadata for.

        Returns:
            dict: A dictionary containing metadata about elements matching the locator.
                The dictionary may contain keys like 'tag', 'id', 'class', 'text', 'attributes', etc.
        """
        pass
