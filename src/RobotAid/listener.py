"""Main Robot Framework listener for healing hooks."""
from pathlib import Path
from robot.api import logger
from robot import result, running
from robot.api.interfaces import ListenerV3

from RobotAid.utils.app_settings import AppSettings
from RobotAid.utils.client_settings import ClientSettings
from RobotAid.self_healing_system.rerun import rerun_keyword_with_fixed_locator
from RobotAid.self_healing_system.kickoff_self_healing import KickoffSelfHealing


class RobotAid(ListenerV3):
    """Robot Framework listener that provides self-healing capabilities."""
    
    ROBOT_LIBRARY_SCOPE = 'SUITE'
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self, config_path: str | None = None):
        """Initialize the healing listener."""
        resolved_path = Path(config_path) if config_path else Path(__file__).resolve().parent / "config.yaml"
        self.app_settings = AppSettings.from_yaml(resolved_path)
        self.client_settings = ClientSettings()

        self.ROBOT_LIBRARY_LISTENER = self
        self.context = {}
        self.enabled = self.app_settings.system.enabled

        self.keyword_try_ctr = 0
        logger.info(f"RobotAid initialized with healing={'enabled' if self.enabled else 'disabled'}")

    def _parse_boolean(self, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', 'y', '1', 'on')
        return bool(value)
    
    def start_test(self, data: running.TestCase, result: result.TestCase):
        """Called when a test starts."""
        if not self.enabled:
            return
        self.context['current_test'] = data.name
        logger.debug(f"RobotAid: Monitoring test '{data.name}'")
    
    def end_keyword(self, data: running.Keyword, result: result.Keyword):
        """Called when a keyword finishes execution."""
        if not self.enabled:
            return
        if result.failed and result.owner == 'Browser':
            logger.debug(f"RobotAid: Detected failure in keyword '{data.name}'")
            if self.keyword_try_ctr < self.app_settings.system.max_retries:
                self.keyword_try_ctr += 1
                locator_suggestion: str = KickoffSelfHealing.kickoff_healing(result=result,
                                                                            app_settings=self.app_settings,
                                                                            client_settings=self.client_settings)
                rerun_keyword_with_fixed_locator(data, locator_suggestion)
                result.status = "PASS"

            self.keyword_try_ctr = 0
            return

    def end_test(self, data: running.TestCase, result: result.TestCase):
        """Called when a test ends."""
        if not self.enabled:
            return

        if result.failed:
            logger.info(f"RobotAid: Test '{data.name}' failed - collecting information for healing")
            # This would store information for post-execution healing