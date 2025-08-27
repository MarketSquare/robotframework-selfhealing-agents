import sys
import types
import pytest
import importlib
from typing import Any
from unittest.mock import MagicMock, patch


def _ensure_robot_stubs() -> None:
    robot_mod = sys.modules.get("robot") or types.ModuleType("robot")
    sys.modules["robot"] = robot_mod

    api_mod = sys.modules.get("robot.api") or types.ModuleType("robot.api")
    logger_obj = getattr(api_mod, "logger", None)

    if logger_obj is None:
        class _Logger:
            def info(self, *a, **k): ...
            def warn(self, *a, **k): ...
        logger_obj = _Logger()

    if not hasattr(logger_obj, "warn"):
        setattr(logger_obj, "warn", lambda *a, **k: None)
    if not hasattr(logger_obj, "info"):
        setattr(logger_obj, "info", lambda *a, **k: None)

    api_mod.logger = logger_obj
    sys.modules["robot.api"] = api_mod

    interfaces_mod = sys.modules.get("robot.api.interfaces") or types.ModuleType("robot.api.interfaces")
    if not hasattr(interfaces_mod, "ListenerV3"):
        class ListenerV3: ...
        interfaces_mod.ListenerV3 = ListenerV3
    sys.modules["robot.api.interfaces"] = interfaces_mod

    running_mod = sys.modules.get("robot.running") or types.ModuleType("robot.running")
    result_mod = sys.modules.get("robot.result") or types.ModuleType("robot.result")
    for m in (running_mod, result_mod):
        if not hasattr(m, "TestCase"):
            class TestCase: ...
            m.TestCase = TestCase
        if not hasattr(m, "Keyword"):
            class Keyword: ...
            m.Keyword = Keyword
    sys.modules["robot.running"] = running_mod
    sys.modules["robot.result"] = result_mod


@pytest.fixture
def listener() -> Any:
    _ensure_robot_stubs()

    sys.modules.pop("SelfhealingAgents.listener", None)
    mod = importlib.import_module("SelfhealingAgents.listener")

    with patch.object(mod, "SelfHealingEngine") as MockEngine, \
         patch.object(mod, "ReportGenerator") as MockReportGen, \
         patch.object(mod, "ListenerState") as MockState, \
         patch.object(mod, "Cfg") as MockCfg:
        mock_engine = MockEngine.return_value
        mock_report_gen = MockReportGen.return_value
        mock_state = MockState.return_value
        mock_state.cfg.enable_self_healing = True
        mock_state.report_info = {"dummy": "info"}
        yield mod.SelfhealingAgents()


def test_initialization_logs_and_sets_state(listener: Any) -> None:
    assert hasattr(listener, "_state")
    assert hasattr(listener, "_self_healing_engine")
    assert hasattr(listener, "_report_generator")
    assert listener._closed is False


def test_start_test_delegates_to_engine(listener: Any) -> None:
    dummy_data = MagicMock()
    dummy_result = MagicMock()
    engine = listener._self_healing_engine
    listener.start_test(dummy_data, dummy_result)
    engine.start_test.assert_called_once_with(dummy_data, dummy_result)


def test_end_keyword_delegates_to_engine(listener: Any) -> None:
    dummy_data = MagicMock()
    dummy_result = MagicMock()
    engine = listener._self_healing_engine
    listener.end_keyword(dummy_data, dummy_result)
    engine.end_keyword.assert_called_once_with(dummy_data, dummy_result)


def test_end_test_delegates_to_engine(listener: Any) -> None:
    dummy_data = MagicMock()
    dummy_result = MagicMock()
    engine = listener._self_healing_engine
    listener.end_test(dummy_data, dummy_result)
    engine.end_test.assert_called_once_with(dummy_data, dummy_result)


def test_close_generates_report_once(listener: Any) -> None:
    report_gen = listener._report_generator
    state = listener._state
    state.report_info = {"dummy": "info"}
    listener.close()
    report_gen.generate_reports.assert_called_once_with(state.report_info)
    listener.close()
    report_gen.generate_reports.assert_called_once()


def test_close_no_report_if_no_info(listener: Any) -> None:
    report_gen = listener._report_generator
    state = listener._state
    state.report_info = None
    listener.close()
    report_gen.generate_reports.assert_not_called()


def test_close_handles_exceptions_gracefully(listener: Any) -> None:
    report_gen = listener._report_generator
    state = listener._state
    state.report_info = {"dummy": "info"}
    report_gen.generate_reports.side_effect = Exception("fail")
    try:
        listener.close()
    except Exception:
        pytest.fail("Exception should not propagate from close()")
