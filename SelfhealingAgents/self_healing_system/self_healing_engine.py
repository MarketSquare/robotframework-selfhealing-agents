from typing import Any, Final

from robot import result, running
from robot.api import logger as rf_logger
from robot.libraries.BuiltIn import BuiltIn
from robot.model import TestCase

from SelfhealingAgents.self_healing_system.kickoff_multi_agent_system import (
    KickoffMultiAgentSystem,
)
from SelfhealingAgents.self_healing_system.schemas.api.locator_healing import (
    LocatorHealingResponse,
    NoHealingNeededResponse,
)
from SelfhealingAgents.self_healing_system.schemas.internal_state.listener_state import (
    ListenerState,
)
from SelfhealingAgents.self_healing_system.schemas.internal_state.report_data import (
    ReportData,
)
from SelfhealingAgents.utils.logfire_init import init_logfire
from SelfhealingAgents.utils.logging import initialize_logger

init_logfire()
initialize_logger()


_ALLOWED_LIBRARIES: Final[frozenset] = frozenset(
    {"Browser", "SeleniumLibrary", "AppiumLibrary"}
)


class SelfHealingEngine:
    """Engine for self-healing test execution in Robot Framework.

    This class manages the self-healing process for test execution failures in Robot Framework.
    It monitors test and keyword execution, triggers locator healing when necessary, and records
    healing attempts and results for reporting.

    Attributes:
        _listener_state (ListenerState): The shared ListenerState object for maintaining state across the test run.
    """

    def __init__(self, listener_state: ListenerState):
        """Initializes the SelfHealingEngine.

        Args:
            listener_state: The shared ListenerState object for maintaining state across the test run.
        """
        self._listener_state: ListenerState = listener_state

    def start_test(self, data: running.TestCase, result_: result.TestCase) -> None:
        """Handles the start of a test case.

        Invoked by listener when a test case starts. Sets up context for self-healing if enabled.

        Args:
            data: The running test case data.
            result_: The result object for the test case.
        """
        if not self._listener_state.cfg.enable_self_healing:
            return
        self._listener_state.context["current_test"] = data.name
        rf_logger.debug(f"SelfhealingAgents: Monitoring test '{data.name}'")

    def end_keyword(self, data: running.Keyword, result_: result.Keyword) -> Any:
        """Handles the end of a keyword execution and triggers self-healing if needed.

        Invoked by listener when a keyword is ended.
        If a keyword fails and is from an allowed library, attempts locator healing and reruns the keyword
        with suggested locators. Updates the result and records the healing attempt if successful.

        Args:
            data: The running keyword data.
            result_: The result object for the keyword.

        Returns:
            None or the return value of the healed keyword execution.
        """
        if not self._listener_state.cfg.enable_self_healing:
            return None
        self._listener_state.healed = False

        # ToDo: Implement a more robust way to start self-healing
        if result_.failed and result_.owner in _ALLOWED_LIBRARIES:
            rf_logger.debug(f"RobotAid: Detected failure in keyword '{data.name}'")
            pre_healing_data: running.Keyword = data.deepcopy()
            if self._listener_state.retry_count < self._listener_state.cfg.max_retries:
                if self._listener_state.should_generate_locators:
                    self._initiate_healing(data, result_)
                keyword_return_value: Any = self._try_locator_suggestions(data)
                # Note: failing suggestions immediately re-trigger end_keyword function

                if self._listener_state.healed:
                    if keyword_return_value and result_.assign:
                        BuiltIn().set_local_variable(
                            result_.assign[0], keyword_return_value
                        )
                    result_.status = "PASS"
                    self._record_report(
                        pre_healing_data,
                        self._listener_state.tried_locators[-1],
                        result_.status,
                    )
            self._reset_state()
        return None

    def end_test(self, data: running.TestCase, result_: result.TestCase) -> None:
        """Handles the end of a test case.

        Invoked by listener when a test case ends. Collects information for post-execution healing if needed.

        Args:
            data: The running test case data.
            result_: The result object for the test case.
        """
        if not self._listener_state.cfg.enable_self_healing:
            return

        if result_.failed:
            rf_logger.info(
                f"RobotAid: Test '{data.name}' failed - collecting information for healing"
            )
            # This would store information for post-execution healing

    def _initiate_healing(self, data: running.Keyword, result_: result.Keyword) -> None:
        """Starts the self-healing process using the agentic system.

        Invokes the multi-agent system to generate locator suggestions and updates the listener state accordingly.

        Args:
            result_: The result object for the failed keyword.
        """
        locator_suggestions: LocatorHealingResponse | str | NoHealingNeededResponse = (
            KickoffMultiAgentSystem.kickoff_healing(
                data,
                result_,
                cfg=self._listener_state.cfg,
                tried_locator_memory=self._listener_state.tried_locators,
            )
        )

        # Only proceed with healing, if response type is LocatorHealingResponse
        if isinstance(locator_suggestions, LocatorHealingResponse):
            self._listener_state.suggestions = locator_suggestions.suggestions
            self._listener_state.should_generate_locators = False
            self._listener_state.retry_count += 1
        elif isinstance(locator_suggestions, NoHealingNeededResponse):
            self._listener_state.suggestions = None
            self._listener_state.should_generate_locators = True
            return

    def _try_locator_suggestions(self, data: running.Keyword) -> Any:
        """Attempts to rerun a keyword with suggested locators.

        Pops a locator suggestion from the list and reruns the keyword with it. Updates healing state and
        returns the result of the rerun.

        Args:
            data: The running keyword data.

        Returns:
            The return value of the rerun keyword, or None if no suggestions remain.
        """
        if not self._listener_state.suggestions:
            return None
        try:
            suggestion: str = self._listener_state.suggestions.pop(0)
        except IndexError:
            return None
        self._listener_state.tried_locators.append(suggestion)
        result: Any = self._rerun_keyword_with_suggested_locator(
            data, suggested_locator=suggestion
        )
        self._listener_state.healed = True
        if not self._listener_state.suggestions:
            self._should_generate_locators = True
        return result

    @staticmethod
    def _rerun_keyword_with_suggested_locator(
        data: running.Keyword, *, suggested_locator: str | None
    ) -> str | None:
        """Reruns a keyword with a suggested locator argument.

        Modifies the keyword arguments to use the suggested locator and executes the keyword again.

        Args:
            data: The running keyword data.
            suggested_locator: The locator string to use for rerunning the keyword.

        Returns:
            The return value of the rerun keyword, or None if no locator is provided.
        """
        if suggested_locator is None:
            return None
        else:
            data.args = list(data.args)
            data.args[0] = suggested_locator
        try:
            try:
                rf_logger.info(
                    f"Re-trying Keyword '{data.name}' with arguments '{data.args}'.",
                    also_console=True,
                )
            except OSError:
                rf_logger.info(
                    f"Re-trying Keyword '{data.name}' with arguments '{data.args}'.",
                    also_console=False,
                )
            return_value: Any = BuiltIn().run_keyword(data.name, *data.args)
            # BuiltIn().run_keyword("Take Screenshot")      # TODO: discuss if this is valuable for other RF-error types
            return return_value
        except Exception as e:
            rf_logger.debug(f"Unexpected error: {e}")
            raise

    def _record_report(
        self,
        data: running.Keyword,
        healed_locator: str,
        status: str,
    ) -> None:
        """Records the result of a healing attempt for reporting.

        Appends a ReportData object to the listener state's report info list.

        Args:
            data: The running keyword data.
            healed_locator: The locator used for healing, if successful.
            status: The status of the keyword execution (e.g., 'PASS').
        """
        args = list(data.args)
        failed_locator: str = BuiltIn().replace_variables(args[0]) if args else ""

        current = data
        locator_origin = current.parent.name
        while current is not None:
            if isinstance(current.parent, TestCase):
                break
            current = getattr(current, "parent", None)

        self._listener_state.report_info.append(
            ReportData(
                file=data.source.parts[-1],
                keyword_source=str(data.source),
                test_name=current.parent.name,
                locator_origin=locator_origin,
                keyword=data.name,
                keyword_args=args,
                lineno=data.lineno,
                failed_locator=failed_locator,
                healed_locator=healed_locator if status == "PASS" else "",
                tried_locators=self._listener_state.tried_locators,
            )
        )

    def _reset_state(self) -> None:
        """Resets the healing state for the next keyword or test.

        Clears locator suggestions, resets retry count, and prepares for the next healing attempt.
        """
        self._listener_state.retry_count = 0
        self._listener_state.suggestions = None
        self._listener_state.should_generate_locators = True
        self._listener_state.tried_locators.clear()
