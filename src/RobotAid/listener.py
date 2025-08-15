from robot.api import logger
from robot import result, running
from robot.api.interfaces import ListenerV3

from RobotAid.utils.cfg import Cfg
from RobotAid.self_healing_system.self_healing_engine import SelfHealingEngine
from RobotAid.self_healing_system.reports.report_generator import ReportGenerator
from RobotAid.self_healing_system.schemas.internal_state.listener_state import ListenerState


class RobotAid(ListenerV3):
    """Robot Framework listener that provides self-healing capabilities."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self) -> None:
        """Initialize the healing listener.

        ToDo: note here in docstrings that state is shared mutable var between listener and SelfHealingEngine
        """
        self.ROBOT_LIBRARY_LISTENER: RobotAid = self
        self._state: ListenerState = ListenerState(cfg=Cfg())   # type: ignore
        self._self_healing_engine: SelfHealingEngine = SelfHealingEngine(self._state)
        self._report_generator: ReportGenerator = ReportGenerator()
        self._closed: bool = False
        logger.info(
            f"RobotAid initialized; healing="
            f"{'enabled' if self._state.cfg.enable_self_healing else 'disabled'}"
        )

    def start_test(
        self, data: running.TestCase, result_: result.TestCase
    ) -> None:
        """Called when a test starts."""
        self._self_healing_engine.start_test(data, result_)

    def end_keyword(
        self, data: running.Keyword, result_: result.Keyword
    ) -> None:
        """Called when a keyword finishes execution."""
        self._self_healing_engine.end_keyword(data, result_)

    def end_test(
        self, data: running.TestCase, result_: result.TestCase
    ) -> None:
        """Called when a test ends."""
        self._self_healing_engine.end_test(data, result_)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._state.report_info:
            self._report_generator.generate_reports(self._state.report_info)
