from typing import Optional

from RobotAid.utils.cfg import Cfg
from RobotAid.self_healing_system.agents.locator_agent.base_locator_agent import BaseLocatorAgent
from RobotAid.self_healing_system.context_retrieving.library_dom_utils.base_dom_utils import BaseDomUtils


class SeleniumLocatorAgent(BaseLocatorAgent):
    """Selenium library specific locator agent implementation.

    This agent is specialized for the Robot Framework SeleniumLibrary.
    It handles Selenium library specific locator formats and validation.
    """

    def __init__(
        self,
        cfg: Cfg,
        dom_utility: Optional[BaseDomUtils] = None,
    ) -> None:
        """Initialize the SeleniumLocatorAgent.

        Args:
            cfg: Instance of Cfg config class containing user defined app configuration.
            usage_limits: Token and request limits for the agent. Defaults to
                UsageLimits with request_limit=5 and total_tokens_limit=2000.
            dom_utility: Optional DOM utility instance for validation.
        """
        super().__init__(cfg, dom_utility)

    def _process_locator(self, locator: str) -> str:
        """Process locator for Selenium library compatibility.

        Args:
            locator: The raw locator string to process.

        Returns:
            The processed locator compatible with Selenium library format.
        """
        return self._convert_locator_to_selenium(locator)

    def _is_locator_valid(self, locator: str) -> bool:
        """Validate locator using Selenium library DOM utilities.

        Args:
            locator: The locator string to validate.

        Returns:
            True if the locator is valid, False otherwise.
            Returns True if DOM utility is not available.
        """
        try:
            return self._dom_utility.is_locator_valid(locator)
        except Exception:
            return False

    @staticmethod
    def is_failed_locator_error(message: str) -> bool:
        """Check if the locator error is due to a failed locator.

        Args:
            message: The error message to check.

        Returns:
            True if the error is due to a failed locator, False otherwise.
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
        """Convert a locator to Selenium library compatible format.

        Args:
            locator: The locator to convert.

        Returns:
            The converted locator compatible with Selenium library.
        """
        locator = locator.strip()
        if locator.startswith("css="):
            locator = "css:" + locator[4:]
        elif locator.startswith("xpath="):
            locator = "xpath:" + locator[6:]
        locator = locator.replace(":has-text", ":contains")
        locator = locator.replace(":text(", "text()=")

        return locator