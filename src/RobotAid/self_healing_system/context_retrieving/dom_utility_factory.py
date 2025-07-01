from enum import Enum
from typing import Optional, Union
from robot.libraries.BuiltIn import BuiltIn
from RobotAid.self_healing_system.context_retrieving.base_dom_utils import BaseDomUtils
from RobotAid.self_healing_system.context_retrieving.browser_dom_utils import BrowserDomUtils
from RobotAid.self_healing_system.context_retrieving.selenium_dom_utils import SeleniumDomUtils
from RobotAid.self_healing_system.context_retrieving.appium_dom_utils import AppiumDomUtils


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
        library_instance: Optional[object] = None
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
        # Auto-detect utility type if not provided
        if utility_type is None:
            utility_type = DomUtilityFactory._auto_detect_utility_type()
        
        # Convert string to enum if necessary
        if isinstance(utility_type, str):
            try:
                utility_type = DomUtilityType(utility_type.lower())
            except ValueError:
                raise ValueError(f"Unsupported DOM utility type: {utility_type}")
        
        # Create the appropriate utility instance
        if utility_type == DomUtilityType.BROWSER:
            return BrowserDomUtils(library_instance)
        elif utility_type == DomUtilityType.SELENIUM:
            return SeleniumDomUtils(library_instance)
        elif utility_type == DomUtilityType.APPIUM:
            return AppiumDomUtils(library_instance)
        else:
            raise ValueError(f"Unsupported DOM utility type: {utility_type}")
    
    @staticmethod
    def _auto_detect_utility_type() -> DomUtilityType:
        """Auto-detect the DOM utility type based on available Robot Framework libraries.
        
        Returns:
            DomUtilityType: The detected utility type.
            
        Raises:
            ValueError: If no supported libraries are detected.
        """
        builtin = BuiltIn()
        
        # Check for Browser library first (preferred for new projects)
        try:
            builtin.get_library_instance('Browser')
            return DomUtilityType.BROWSER
        except Exception:
            pass
        
        # Check for SeleniumLibrary
        try:
            builtin.get_library_instance('SeleniumLibrary')
            return DomUtilityType.SELENIUM
        except Exception:
            pass
        
        # Check for AppiumLibrary
        try:
            builtin.get_library_instance('AppiumLibrary')
            return DomUtilityType.APPIUM
        except Exception:
            pass
        
        # Default to Browser if no libraries are detected (for testing scenarios)
        print("Warning: No supported Robot Framework libraries detected. Defaulting to Browser utility.")
        return DomUtilityType.BROWSER
    
    @staticmethod
    def get_supported_types() -> list[str]:
        """Get a list of supported DOM utility types.
        
        Returns:
            list[str]: List of supported utility type strings.
        """
        return [utility.value for utility in DomUtilityType]
    
    @staticmethod
    def detect_library_from_keyword_result(result) -> Optional[DomUtilityType]:
        """Detect the DOM utility type from a Robot Framework keyword result.
        
        Args:
            result: Robot Framework keyword result object with an 'owner' attribute.
            
        Returns:
            DomUtilityType: The detected utility type, or None if not detected.
        """
        if not hasattr(result, 'owner'):
            return None
            
        owner = getattr(result, 'owner', '').lower()
        
        if 'browser' in owner:
            return DomUtilityType.BROWSER
        elif 'selenium' in owner:
            return DomUtilityType.SELENIUM
        elif 'appium' in owner:
            return DomUtilityType.APPIUM
        
        return None
