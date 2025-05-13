"""Main Robot Framework listener for healing hooks."""
import os
from robot.api import logger
from robot import result, running
from robot.api.interfaces import ListenerV3

from pathlib import Path
from RobotAid.utils.app_settings import AppSettings
from RobotAid.utils.client_settings import ClientSettings
from RobotAid.self_healing_system.kickoff_self_healing import KickoffSelfHealing


class RobotAid(ListenerV3):
    """Robot Framework listener that provides self-healing capabilities."""
    
    ROBOT_LIBRARY_SCOPE = 'SUITE'
    ROBOT_LISTENER_API_VERSION = 3
    
    def __init__(self):
        """Initialize the healing listener."""
        config_base_dir: str = os.path.dirname(os.path.abspath(__file__))
        config_path: Path = Path(config_base_dir) / "config.yaml"
        self.app_settings = AppSettings.from_yaml(config_path)
        self.client_settings = ClientSettings()

        self.ROBOT_LIBRARY_LISTENER = self
        self.context = {}
        self.enabled = self.app_settings.system.enabled
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
        if result.failed  and result.type.strip().casefold() == 'keyword':
            logger.debug(f"RobotAid: Detected failure in keyword '{data.name}'")
            KickoffSelfHealing.kickoff_healing(result=result,
                                               app_settings=self.app_settings,
                                               client_settings=self.client_settings)
            
    def end_test(self, data: running.TestCase, result: result.TestCase):
        """Called when a test ends."""
        if not self.enabled:
            return
            
        if result.failed:
            logger.info(f"RobotAid: Test '{data.name}' failed - collecting information for healing")
            # This would store information for post-execution healing