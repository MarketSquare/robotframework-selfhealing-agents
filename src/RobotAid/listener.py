"""Main Robot Framework listener for healing hooks."""

from pathlib import Path

from robot import result, running
from robot.api import logger
from robot.api.interfaces import ListenerV3

from RobotAid.self_healing_system.kickoff_self_healing import KickoffSelfHealing
from RobotAid.self_healing_system.rerun import rerun_keyword_with_fixed_locator
from RobotAid.self_healing_system.schemas import LocatorHealingResponse
from RobotAid.utils.app_settings import AppSettings
from RobotAid.utils.client_settings import ClientSettings


class RobotAid(ListenerV3):
    """Robot Framework listener that provides self-healing capabilities."""

    ROBOT_LIBRARY_SCOPE = "SUITE"
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self, config_path: str | None = None):
        """Initialize the healing listener."""
        resolved_path = (
            Path(config_path)
            if config_path
            else Path(__file__).resolve().parent / "config.yaml"
        )
        self.app_settings = AppSettings.from_yaml(resolved_path)
        self.client_settings = ClientSettings()

        self.ROBOT_LIBRARY_LISTENER = self
        self.context = {}
        self.enabled = self.app_settings.system.enabled

        self.keyword_try_ctr = 0
        self.suggestions = None
        self.generate_suggestions = True
        self.tried_locator_memory = list()
        logger.info(
            f"RobotAid initialized with healing={'enabled' if self.enabled else 'disabled'}"
        )

    def _parse_boolean(self, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "yes", "y", "1", "on")
        return bool(value)

    def start_test(self, data: running.TestCase, result: result.TestCase):
        """Called when a test starts."""
        if not self.enabled:
            return
        self.context["current_test"] = data.name
        logger.debug(f"RobotAid: Monitoring test '{data.name}'")

    def end_keyword(self, data: running.Keyword, result: result.Keyword):
        """Called when a keyword finishes execution."""
        if not self.enabled:
            return
        # ToDo: Implement a more robust way to start self-healing
        if result.failed and result.owner in [
            "Browser",
            "SeleniumLibrary",
            "AppiumLibrary",
        ]:
            logger.debug(f"RobotAid: Detected failure in keyword '{data.name}'")
            if self.keyword_try_ctr < self.app_settings.system.max_retries:
                if self.generate_suggestions:
                    self._start_self_healing(result=result)
                self._try_locator_suggestions(
                    data=data
                )  # Note: failing suggestions immediately re-trigger
                #       end_keyword function
                result.status = "PASS"

            self.keyword_try_ctr = 0
            self.suggestions = None
            self.generate_suggestions = True
            self.tried_locator_memory = list()
            return

    def end_test(self, data: running.TestCase, result: result.TestCase):
        """Called when a test ends."""
        if not self.enabled:
            return

        if result.failed:
            logger.info(
                f"RobotAid: Test '{data.name}' failed - collecting information for healing"
            )
            # This would store information for post-execution healing

    def _start_self_healing(self, result: result.Keyword) -> None:
        """Starts the self-healing process via pydanticAI agentic system. Sets class attributes for further processing."""
        locator_suggestions: LocatorHealingResponse = (
            KickoffSelfHealing.kickoff_healing(
                result=result,
                app_settings=self.app_settings,
                client_settings=self.client_settings,
                tried_locator_memory=self.tried_locator_memory,
            )
        )
        self.suggestions = locator_suggestions.suggestions
        self.generate_suggestions = False
        self.keyword_try_ctr += 1

    def _try_locator_suggestions(self, data: running.Keyword) -> None:
        """Reruns a locator suggestion that is stored in the class attribute list."""
        current_suggestion = None
        try:
            current_suggestion = self.suggestions[0]
            self.suggestions.pop(0)
            if len(self.suggestions) == 0:
                self.suggestions = None
                self.generate_suggestions = True
        except:
            pass

        if current_suggestion:
            self.tried_locator_memory.append(current_suggestion)
            rerun_keyword_with_fixed_locator(data, current_suggestion)
