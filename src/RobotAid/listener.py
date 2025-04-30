"""Main Robot Framework listener for healing hooks."""

from robot.libraries.BuiltIn import BuiltIn
from robot.api import logger


class RobotAid:
    """Robot Framework listener that provides self-healing capabilities."""
    
    ROBOT_LIBRARY_SCOPE = 'SUITE'
    ROBOT_LISTENER_API_VERSION = 3
    
    def __init__(self, enabled=True, max_retries=3, llm_provider=None):
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
    
    def start_test(self, name, attrs):
        """Called when a test starts."""
        if not self.enabled:
            return
        
        self.context['current_test'] = name
        logger.debug(f"RobotAid: Monitoring test '{name}'")
    
    def end_keyword(self, name, attrs):
        """Called when a keyword finishes execution."""
        if not self.enabled:
            return
            
        if attrs.get('status') == 'FAIL' and attrs.get('type') == 'Keyword':
            logger.debug(f"RobotAid: Detected failure in keyword '{name}'")
            # This would be where healing logic is triggered
            # For now just log the detection
            
    def end_test(self, name, attrs):
        """Called when a test ends."""
        if not self.enabled:
            return
            
        if attrs.get('status') == 'FAIL':
            logger.info(f"RobotAid: Test '{name}' failed - collecting information for healing")
            # This would store information for post-execution healing