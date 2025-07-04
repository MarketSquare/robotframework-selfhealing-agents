from typing import Optional

from bs4 import BeautifulSoup
from robot.libraries.BuiltIn import BuiltIn

from RobotAid.self_healing_system.context_retrieving.base_dom_utils import \
    BaseDomUtils
from RobotAid.self_healing_system.context_retrieving.dom_soap_utils import \
    SoupDomUtils


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
                library_instance = BuiltIn().get_library_instance('SeleniumLibrary')
            except Exception:
                print("SeleniumLibrary is not available. Selenium DOM utility will be limited.")
                library_instance = None
        
        super().__init__(library_instance)

    def is_locator_unique(self, locator: str) -> bool:
        """Check if the locator is unique using Selenium library methods.
        
        Args:
            locator (str): The locator to check.
            
        Returns:
            bool: True if the locator is unique, False otherwise.
        """
        if self.library_instance is None:
            return True  # Skip validation if library is not available
            
        try:
            # Use dynamic attribute access to handle different SeleniumLibrary versions
            elements = getattr(self.library_instance, 'get_webelements')(locator)
            return len(elements) == 1
        except Exception:
            return False

    def is_locator_visible(self, locator: str) -> bool:
        """Check if the locator is visible using Selenium library methods.
        
        Args:
            locator (str): The locator to check.
            
        Returns:
            bool: True if the locator is visible, False otherwise.
        """
        if self.library_instance is None:
            return True  # Skip validation if library is not available
            
        try:
            # Use dynamic attribute access for element visibility check
            getattr(self.library_instance, 'element_should_be_visible')(locator)
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
            # Get page source using SeleniumLibrary
            page_source = getattr(self.library_instance, 'get_source')()
            
            soup: BeautifulSoup = BeautifulSoup(page_source, 'html.parser')
            source: str = SoupDomUtils().get_simplified_dom_tree(str(soup.body) if soup.body else str(soup))
            return source
            
        except Exception as e:
            return f"<html><body>Error retrieving DOM tree: {str(e)}</body></html>"

    def get_library_type(self) -> str:
        """Get the library type identifier.
        
        Returns:
            str: The library type identifier.
        """
        return "selenium"
