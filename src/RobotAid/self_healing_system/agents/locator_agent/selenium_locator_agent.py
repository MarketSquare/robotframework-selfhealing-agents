from typing import Optional

from RobotAid.utils.cfg import Cfg
from RobotAid.self_healing_system.agents.locator_agent.base_locator_agent import BaseLocatorAgent
from RobotAid.self_healing_system.context_retrieving.library_dom_utils.base_dom_utils import BaseDomUtils


class SeleniumLocatorAgent(BaseLocatorAgent):
    """Selenium library-specific locator agent implementation.

    This agent is specialized for the Robot Framework SeleniumLibrary.
    It handles Selenium library-specific locator formats and validation.
    """
    def __init__(
        self,
        cfg: Cfg,
        dom_utility: Optional[BaseDomUtils] = None,
    ) -> None:
        """Initializes the SeleniumLocatorAgent.

        Args:
            cfg (Cfg): Instance of Cfg config class containing user-defined app configuration.
            dom_utility (Optional[BaseDomUtils]): Optional DOM utility instance for validation.
        """
        super().__init__(cfg, dom_utility)

    def _process_locator(self, locator: str) -> str:
        """Processes a locator for Selenium library compatibility.

        Args:
            locator (str): The raw locator string to process.

        Returns:
            str: The processed locator compatible with Selenium library format.
        """
        return self._convert_locator_to_selenium(locator)

    def _is_locator_valid(self, locator: str) -> bool:
        """Validates a locator using Selenium library DOM utilities.

        Args:
            locator (str): The locator string to validate.

        Returns:
            bool: True if the locator is valid, False otherwise. Returns True if DOM utility is not available.
        """
        try:
            return self._dom_utility.is_locator_valid(locator)
        except Exception:
            return False

    @staticmethod
    def is_failed_locator_error(message: str) -> bool:
        """Checks if the error message is due to a failed locator.

        Args:
            message (str): The error message to check.

        Returns:
            bool: True if the error is due to a failed locator, False otherwise.
        """
        return (
            ("with locator" in message and "not found" in message)
            or ("No element with locator" in message and "found" in message)
            or ("No radio button with name" in message and "found" in message)
            or ("Page should have contained" in message)
            or ("invalid element state" in message)
        )

    @staticmethod
    def _convert_locator_to_selenium(locator: str) -> str:
        """Converts a locator to Selenium library compatible format.

        Args:
            locator (str): The locator to convert.

        Returns:
            str: The converted locator compatible with Selenium library.
        """
        locator: str = locator.strip()
        if locator.startswith("css="):
            locator: str = "css:" + locator[4:]
        elif locator.startswith("xpath="):
            locator: str = "xpath:" + locator[6:]
        locator: str = locator.replace(":has-text", ":contains")
        locator: str = locator.replace(":text(", "text()=")

        return locator