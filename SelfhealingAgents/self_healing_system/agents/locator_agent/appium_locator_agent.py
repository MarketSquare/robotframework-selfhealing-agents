from typing import Optional

from SelfhealingAgents.utils.cfg import Cfg
from SelfhealingAgents.self_healing_system.agents.locator_agent.base_locator_agent import BaseLocatorAgent
from SelfhealingAgents.self_healing_system.context_retrieving.library_dom_utils.base_dom_utils import BaseDomUtils


class AppiumLocatorAgent(BaseLocatorAgent):
    """Appium library-specific locator agent implementation.

    Handles Appium-specific locator formats (XPath/accessibility/resource-id) and validation.
    """

    def __init__(
        self,
        cfg: Cfg,
        dom_utility: Optional[BaseDomUtils] = None,
    ) -> None:
        super().__init__(cfg, dom_utility)

    def _process_locator(self, locator: str) -> str:
        """Normalizes locators for Appium.

        Accepts raw XPath (//...), or prefixed forms (xpath= / xpath: ).
        Leaves accessibility/resource-id strategies as-is.
        """
        loc = (locator or "").strip()
        if loc.startswith("xpath:"):
            loc = "xpath=" + loc[len("xpath:") :]
        # AppiumLibrary accepts both raw XPath and prefixed
        return loc

    def _is_locator_valid(self, locator: str) -> bool:
        try:
            return self._dom_utility.is_locator_valid(locator)
        except Exception:
            return False

    @staticmethod
    def is_failed_locator_error(message: str) -> bool:
        """Detects common Appium element-not-found errors.

        Covers WebDriver/Appium phrasing seen across platforms.
        """
        msg = (message or "").lower()
        return (
            "no such element" in msg
            or "could not locate element" in msg
            or ("element" in msg and "not found" in msg)
            or "unable to locate" in msg
            or "did not match any elements" in msg
        )
