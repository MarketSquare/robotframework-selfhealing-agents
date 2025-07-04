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
    def is_locator_unique(self, locator: str) -> bool:
        """Check if the given locator is unique in the DOM.
        
        Args:
            locator (str): The locator to check.
            
        Returns:
            bool: True if the locator is unique, False otherwise.
        """
        pass

    @abstractmethod
    def is_locator_visible(self, locator: str) -> bool:
        """Check if the given locator is visible in the DOM.
        
        Args:
            locator (str): The locator to check.
            
        Returns:
            bool: True if the locator is visible, False otherwise.
        """
        pass

    @abstractmethod
    def get_dom_tree(self) -> str:
        """Retrieve the DOM tree of the current page.
        
        Returns:
            str: The DOM tree as a string.
        """
        pass

    @abstractmethod
    def get_library_type(self) -> str:
        """Get the library type identifier.
        
        Returns:
            str: The library type (e.g., 'browser', 'selenium', 'appium').
        """
        pass
