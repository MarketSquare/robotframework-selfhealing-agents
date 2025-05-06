"""Main Robot Framework listener for healing hooks."""

from robot.api import logger
from robot import result, running
from robot.api.interfaces import ListenerV3
from RobotAid.self_healing_system.kickoff_self_healing import kickoff_healing


class RobotAid(ListenerV3):
    """Robot Framework listener that provides self-healing capabilities."""
    
    ROBOT_LIBRARY_SCOPE = 'SUITE'
    ROBOT_LISTENER_API_VERSION = 3
    
    def __init__(self, enabled=True, max_retries=3, llm_provider="openai"):
        """Initialize the healing listener.
        
        Args:
            enabled (bool): Whether healing is enabled
            max_retries (int): Maximum number of retry attempts
            llm_provider (str, optional): LLM provider to use
        """
        self.enabled = self._parse_boolean(enabled)
        self.max_retries = int(max_retries)
        self.llm_provider = llm_provider
        self.context = {}
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
            # for now, only a dummy healing process triggered with temporary arbitrary payload; context and further
            # information will be implemented soon
            kickoff_healing(llm_provider=self.llm_provider)
            
    def end_test(self, data: running.TestCase, result: result.TestCase):
        """Called when a test ends."""
        if not self.enabled:
            return
            
        if result.failed:
            logger.info(f"RobotAid: Test '{data.name}' failed - collecting information for healing")
            # This would store information for post-execution healing