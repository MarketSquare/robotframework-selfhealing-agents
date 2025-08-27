from SelfhealingAgents.utils.cfg import Cfg
from SelfhealingAgents.utils.reponse_converters import convert_locator_to_browser
from SelfhealingAgents.self_healing_system.agents.locator_agent.base_locator_agent import BaseLocatorAgent
from SelfhealingAgents.self_healing_system.context_retrieving.library_dom_utils.base_dom_utils import BaseDomUtils


class BrowserLocatorAgent(BaseLocatorAgent):
    """Browser library-specific locator agent implementation.

    This agent is specialized for the Robot Framework Browser library (Playwright-based).
    It handles Browser library-specific locator formats and validation.
    """
    def __init__(
        self,
        cfg: Cfg,
        dom_utility: BaseDomUtils,
    ) -> None:
        """Initializes the BrowserLocatorAgent.

        Args:
            cfg (Cfg): Instance of Cfg config class containing user-defined app configuration.
            dom_utility (BaseDomUtils): DOM utility instance for validation.
        """
        super().__init__(cfg, dom_utility)

    def _process_locator(self, locator: str) -> str:
        """Processes a locator for Browser library compatibility.

        Args:
            locator (str): The raw locator string to process.

        Returns:
            str: The processed locator compatible with Browser library format.
        """
        return convert_locator_to_browser(locator)

    def _is_locator_valid(self, locator: str) -> bool:
        """Validates a locator using Browser library DOM utilities.

        Args:
            locator (str): The locator string to validate.

        Returns:
            bool: True if the locator is valid and unique, False otherwise. Returns True if DOM utility is not available.
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
            "waiting for locator" in message
            and "waiting for element to be" not in message
        ) or "Element is not an" in message
