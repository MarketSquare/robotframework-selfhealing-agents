from typing import Final, Optional, Any

from robot.api import logger
from robot import result, running
from robot.libraries.BuiltIn import BuiltIn

from RobotAid.self_healing_system.schemas.internal_state.report_data import ReportData
from RobotAid.self_healing_system.kickoff_multi_agent_system import KickoffMultiAgentSystem
from RobotAid.self_healing_system.schemas.internal_state.listener_state import ListenerState
from RobotAid.self_healing_system.schemas.api.locator_healing import (
    LocatorHealingResponse,
    NoHealingNeededResponse,
)

_ALLOWED_LIBRARIES: Final[frozenset] = frozenset(
    {"Browser", "SeleniumLibrary", "AppiumLibrary"}
)


class SelfHealingEngine:

    def __init__(self, listener_state: ListenerState):
        self._listener_state = listener_state

    def start_test(
            self, data: running.TestCase, result_: result.TestCase
    ) -> None:
        """Called when a test starts."""
        if not self._listener_state.cfg.enable_self_healing:
            return
        self._listener_state.context["current_test"] = data.name
        logger.debug(f"RobotAid: Monitoring test '{data.name}'")

    def end_keyword(
            self, data: running.Keyword, result_: result.Keyword
    ) -> Optional[Any]:
        if not self._listener_state.cfg.enable_self_healing:
            return None
        self._listener_state.healed = False

        # ToDo: Implement a more robust way to start self-healing
        if result_.failed and result_.owner in _ALLOWED_LIBRARIES:
            logger.debug(f"RobotAid: Detected failure in keyword '{data.name}'")
            pre_healing_data = data.deepcopy()
            if self._listener_state.retry_count < self._listener_state.cfg.max_retries:
                if self._listener_state.should_generate_locators:
                    self._initiate_healing(result_)
                keyword_return_value = self._try_locator_suggestions(data)
                # Note: failing suggestions immediately re-trigger end_keyword function

                if self._listener_state.healed:
                    if keyword_return_value and result_.assign:
                        BuiltIn().set_local_variable(result_.assign[0], keyword_return_value)
                    result_.status = "PASS"
                    self._record_report(pre_healing_data, self._listener_state.tried_locators[-1], result_.status)
            self._reset_state()
        return None

    def end_test(
        self, data: running.TestCase, result_: result.TestCase
    ) -> None:
        """Called when a test ends."""
        if not self._listener_state.cfg.enable_self_healing:
            return

        if result_.failed:
            logger.info(
                f"RobotAid: Test '{data.name}' failed - collecting information for healing"
            )
            # This would store information for post-execution healing

    def _initiate_healing(self, result_: result.Keyword) -> None:
        """Starts the self-healing process via pydanticAI agentic system.
           Sets class attributes for further processing.
        """
        locator_suggestions: LocatorHealingResponse | str | NoHealingNeededResponse = (
            KickoffMultiAgentSystem.kickoff_healing(
                result=result_,
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

    def _try_locator_suggestions(self, data: running.Keyword) -> Optional[Any]:
        """Reruns a locator suggestion that is stored in the class attribute list."""
        if not self._listener_state.suggestions:
            return None
        try:
            suggestion = self._listener_state.suggestions.pop(0)
        except IndexError:
            return None
        self._listener_state.tried_locators.append(suggestion)
        result = self._rerun_keyword_with_fixed_locator(data, suggestion)
        self._listener_state.healed = True
        if not self._listener_state.suggestions:
            self._should_generate_locators = True
        return result

    @staticmethod
    def _rerun_keyword_with_fixed_locator(
            data: Any, fixed_locator: Optional[str] = None
    ) -> str:
        if fixed_locator:
            data.args = list(data.args)
            data.args[0] = fixed_locator
        try:
            logger.info(
                f"Re-trying Keyword '{data.name}' with arguments '{data.args}'.",
                also_console=True,
            )
            return_value = BuiltIn().run_keyword(data.name, *data.args)
            # BuiltIn().run_keyword("Take Screenshot")      # TODO: discuss if this is valuable for other RF-error types
            return return_value
        except Exception as e:
            logger.debug(f"Unexpected error: {e}")
            raise

    def _record_report(
        self,
        data: running.Keyword,
        healed_locator: str,
        status: str,
    ) -> None:
        args = data.args
        failed_locator = BuiltIn().replace_variables(args[0]) if args else ""
        self._listener_state.report_info.append(
            ReportData(
                file=data.source.parts[-1],
                keyword_source=str(data.source),
                test_name=data.parent.name,
                keyword=data.name,
                keyword_args=args,
                lineno=data.lineno,
                failed_locator=failed_locator,
                healed_locator=healed_locator if status == "PASS" else "",
                tried_locators=self._listener_state.tried_locators,
            )
        )

    def _reset_state(self) -> None:
        self._listener_state.retry_count = 0
        self._listener_state.suggestions = None
        self._listener_state.should_generate_locators = True
        self._listener_state.tried_locators.clear()
