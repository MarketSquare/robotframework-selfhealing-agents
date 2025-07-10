from typing import Optional

from pydantic_ai.usage import UsageLimits

from RobotAid.self_healing_system.agents.base_locator_agent import \
    BaseLocatorAgent
from RobotAid.self_healing_system.agents.prompts import PromptsLocator
from RobotAid.self_healing_system.context_retrieving.base_dom_utils import \
    BaseDomUtils
from RobotAid.self_healing_system.context_retrieving.dom_utility_factory import (
    DomUtilityFactory, DomUtilityType)
from RobotAid.utils.app_settings import AppSettings
from RobotAid.utils.client_settings import ClientSettings


def convert_locator_to_selenium(locator: str) -> str:
    """Convert a locator to Selenium library compatible format.
    
    Args:
        locator (str): The locator to convert.
        
    Returns:
        str: The converted locator compatible with Selenium library.
    """
    locator = locator.strip()
    
    if locator.startswith("css="):
        locator = "css:" + locator[4:]
    elif locator.startswith("xpath="):
        locator = "xpath:" + locator[6:]
    
    locator = locator.replace(":has-text", ":contains")
    locator = locator.replace(":text(", "text()=")
    
    return locator


class SeleniumLocatorAgent(BaseLocatorAgent):
    """Selenium library specific locator agent implementation.
    
    This agent is specialized for the Robot Framework SeleniumLibrary.
    It handles Selenium library specific locator formats and validation.
    """
    
    def __init__(
        self,
        app_settings: AppSettings,
        client_settings: ClientSettings,
        usage_limits: UsageLimits = UsageLimits(request_limit=5, total_tokens_limit=2000),
        dom_utility: Optional[BaseDomUtils] = None
    ) -> None:
        if dom_utility is None:
            try:
                self.dom_utility = DomUtilityFactory.create_dom_utility(DomUtilityType.SELENIUM)
            except Exception as e:
                print(f"SeleniumDomUtils initialization failed: {e}. Skipping DOM utility initialization.")
                self.dom_utility = None
        else:
            self.dom_utility = dom_utility
            
        super().__init__(app_settings, client_settings, usage_limits)

    def _get_system_prompt(self) -> str:
        """Get the Selenium library specific system prompt."""
        return (
            f"{PromptsLocator.system_msg}\n"
            "SELENIUM LIBRARY SPECIFIC INSTRUCTIONS:\n"
            "- Keywords like 'Input Text', 'Input Password' or 'Press Keys'  are always related to 'input' or 'textarea' elements.\n"
            "- Keywords like 'Click' are often  related to 'button','checkbox', 'a' or 'input' elements.\n"
            "- Keywords like 'Select From List' are often related to 'select' elements.\n"
            "- Keywords like 'Select Checkbox' are often related to 'checkbox' elements.\n"
            "- Prefix CSS selectors with 'css:' \n"
            "- Prefix XPath expressions with 'xpath:'\n"
            '- Example response: {"suggestions": ["css:input[id=\'my_id\']", "xpath://*[contains(text(),\'Login\')]", "css:button:contains(Submit)"]}\n'
        )

    def _process_locator(self, locator: str) -> str:
        """Process locator for Selenium library compatibility."""
        return convert_locator_to_selenium(locator)

    def _is_locator_valid(self, locator: str) -> bool:
        """Validate locator using Selenium library DOM utilities."""
        if self.dom_utility is None:
            return True  # Skip validation if DOM utility is not available
        
        try:
            return self.dom_utility.is_locator_unique(locator)
        except Exception:
            return False

    def get_agent_type(self) -> str:
        """Get the agent type identifier."""
        return "selenium"
