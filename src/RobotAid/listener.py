from robot.api import logger
from robot import result, running
from robot.api.interfaces import ListenerV3

from RobotAid.utils.cfg import Cfg
from RobotAid.self_healing_system.self_healing_engine import SelfHealingEngine
from RobotAid.self_healing_system.reports.report_generator import ReportGenerator
from RobotAid.self_healing_system.schemas.internal_state.listener_state import ListenerState


class RobotAid(ListenerV3):
    """Robot Framework listener that provides self-healing capabilities.

    This listener integrates with Robot Framework to enable self-healing test execution.
    It manages the internal state, coordinates the self-healing engine, and generates reports
    based on test execution outcomes.

    Attributes:
        ROBOT_LIBRARY_SCOPE (str): The scope of the Robot Framework library ('GLOBAL').
        ROBOT_LISTENER_API_VERSION (int): The Robot Framework listener API version (3).
        ROBOT_LIBRARY_LISTENER (RobotAid): Reference to the listener instance (set to self).
        _state (ListenerState): The internal state object shared with the self-healing engine.
        _self_healing_engine (SelfHealingEngine): The self-healing engine instance.
        _report_generator (ReportGenerator): The report generator instance.
        _closed (bool): Whether the listener has been closed.
    """
    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self) -> None:
        """Initializes the RobotAid listener and its components.

        The "_state" attribute of type ListenerState is shared and manipulated
        in the self_healing_engine module.
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
        """Handles the start of a test case.

        Invoked by Robot Framework when a test case starts. Delegates to the self-healing engine.

        Args:
            data: The running test case data.
            result_: The result object for the test case.
        """
        self._self_healing_engine.start_test(data, result_)

    def end_keyword(
        self, data: running.Keyword, result_: result.Keyword
    ) -> None:
        """Handles the end of a keyword execution.

        Invoked by Robot Framework when a keyword finishes execution. Delegates to the self-healing engine.

        Args:
            data: The running keyword data.
            result_: The result object for the keyword.
        """
        self._self_healing_engine.end_keyword(data, result_)

    def end_test(
        self, data: running.TestCase, result_: result.TestCase
    ) -> None:
        """Handles the end of a test case.

        Invoked by Robot Framework when a test case ends. Delegates to the self-healing engine.

        Args:
            data: The running test case data.
            result_: The result object for the test case.
        """
        self._self_healing_engine.end_test(data, result_)

    def close(self) -> None:
        """Handles the closure of the test suite or all suites when scope is 'GLOBAL'.

        Generates reports if report information is available and ensures closure is performed only once.
        """
        if self._closed:
            return
        self._closed = True
        if self._state.report_info:
            self._report_generator.generate_reports(self._state.report_info)
