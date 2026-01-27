import sys
import types
import pytest
import importlib
from pathlib import Path
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
def listener(tmp_path: Path) -> Any:
    _ensure_robot_stubs()

    orig_cwd = Path.cwd()
    try:
        import os
        os.chdir(tmp_path)

        sys.modules.pop("SelfhealingAgents.listener", None)
        mod = importlib.import_module("SelfhealingAgents.listener")

        with patch.object(mod, "SelfHealingEngine") as MockEngine, \
                patch.object(mod, "ReportGenerator") as MockReportGen, \
                patch.object(mod, "ListenerState") as MockState, \
                patch.object(mod, "Cfg") as MockCfg, \
                patch.object(mod, "save_report_info") as mock_save_report_info, \
                patch.object(mod, "load_report_info") as mock_load_report_info, \
                patch.object(mod, "deduplicate_report_info") as mock_dedup, \
                patch.object(mod, "sort_report_info") as mock_sort:
            mock_cfg = MockCfg.return_value
            mock_cfg.enable_self_healing = True
            mock_cfg.is_rerun_activated = False
            mock_cfg.report_directory = tmp_path

            mock_state = MockState.return_value
            mock_state.cfg = mock_cfg
            mock_state.report_info = None

            mock_engine = MockEngine.return_value
            mock_report_gen = MockReportGen.return_value

            mod._test_mocks = {
                "engine": mock_engine,
                "report_gen": mock_report_gen,
                "state": mock_state,
                "cfg": mock_cfg,
                "save_report_info": mock_save_report_info,
                "load_report_info": mock_load_report_info,
                "dedup": mock_dedup,
                "sort": mock_sort,
            }

            inst = mod.SelfhealingAgents()
            yield inst

    finally:
        import os
        os.chdir(orig_cwd)


def _get_internals(listener: Any) -> dict[str, Any]:
    mod = importlib.import_module("SelfhealingAgents.listener")
    return mod._test_mocks  # type: ignore[attr-defined]


def test_initialization_logs_and_sets_state(listener: Any) -> None:
    assert hasattr(listener, "_state")
    assert hasattr(listener, "_self_healing_engine")
    assert hasattr(listener, "_report_generator")
    assert listener._closed is False


def test_start_test_delegates_to_engine(listener: Any) -> None:
    internals = _get_internals(listener)
    engine = internals["engine"]

    dummy_data = MagicMock()
    dummy_result = MagicMock()
    listener.start_test(dummy_data, dummy_result)
    engine.start_test.assert_called_once_with(dummy_data, dummy_result)


def test_end_keyword_delegates_to_engine(listener: Any) -> None:
    internals = _get_internals(listener)
    engine = internals["engine"]

    dummy_data = MagicMock()
    dummy_result = MagicMock()
    listener.end_keyword(dummy_data, dummy_result)
    engine.end_keyword.assert_called_once_with(dummy_data, dummy_result)


def test_end_test_delegates_to_engine(listener: Any) -> None:
    internals = _get_internals(listener)
    engine = internals["engine"]

    dummy_data = MagicMock()
    dummy_result = MagicMock()
    listener.end_test(dummy_data, dummy_result)
    engine.end_test.assert_called_once_with(dummy_data, dummy_result)


def test_close_no_rerun_no_report_info(listener: Any) -> None:
    internals = _get_internals(listener)
    report_gen = internals["report_gen"]
    state = internals["state"]
    cfg = internals["cfg"]

    cfg.is_rerun_activated = False
    state.report_info = None

    listener.close()
    report_gen.generate_reports.assert_not_called()


def test_close_no_rerun_report_generation_exception_is_swallowed(listener: Any) -> None:
    internals = _get_internals(listener)
    report_gen = internals["report_gen"]
    state = internals["state"]
    cfg = internals["cfg"]

    cfg.is_rerun_activated = False
    state.report_info = [{"dummy": "info"}]
    report_gen.generate_reports.side_effect = Exception("fail")

    try:
        listener.close()
    except Exception:
        pytest.fail("Exception should not propagate from close() when no rerun is activated")

    report_gen.generate_reports.assert_called_once_with(state.report_info)


def test_close_rerun_initial_run_persists_and_generates(listener: Any, tmp_path: Path) -> None:
    internals = _get_internals(listener)
    report_gen = internals["report_gen"]
    state = internals["state"]
    cfg = internals["cfg"]
    save_report_info = internals["save_report_info"]

    cfg.is_rerun_activated = True
    state.report_info = [{"dummy": "info"}]

    from SelfhealingAgents.self_healing_system.reports.report_info_persistence import REPORT_INFO_FILE
    json_path = Path.cwd() / REPORT_INFO_FILE.name
    if json_path.exists():
        json_path.unlink()

    listener.close()

    save_report_info.assert_called_once_with(state.report_info, json_path)
    report_gen.generate_reports.assert_called_once_with(state.report_info)


def test_close_rerun_initial_run_no_report_info(listener: Any) -> None:
    internals = _get_internals(listener)
    report_gen = internals["report_gen"]
    state = internals["state"]
    cfg = internals["cfg"]
    save_report_info = internals["save_report_info"]

    cfg.is_rerun_activated = True
    state.report_info = None

    from SelfhealingAgents.self_healing_system.reports.report_info_persistence import REPORT_INFO_FILE
    json_path = Path.cwd() / REPORT_INFO_FILE.name
    if json_path.exists():
        json_path.unlink()

    listener.close()

    save_report_info.assert_not_called()
    report_gen.generate_reports.assert_not_called()


def test_close_rerun_second_run_merges_and_generates_and_cleans_up(listener: Any) -> None:
    internals = _get_internals(listener)
    report_gen = internals["report_gen"]
    state = internals["state"]
    cfg = internals["cfg"]
    save_report_info = internals["save_report_info"]
    load_report_info = internals["load_report_info"]
    dedup = internals["dedup"]
    sort = internals["sort"]

    cfg.is_rerun_activated = True
    state.report_info = [{"run": 2}]

    from SelfhealingAgents.self_healing_system.reports.report_info_persistence import REPORT_INFO_FILE
    json_path = Path.cwd() / REPORT_INFO_FILE.name

    json_path.write_text("[]")
    previous = [{"run": 1}]
    load_report_info.return_value = previous

    combined = previous + state.report_info
    deduped = combined
    ordered = list(reversed(deduped))
    dedup.return_value = deduped
    sort.return_value = ordered

    listener.close()

    load_report_info.assert_called_once_with(json_path)
    dedup.assert_called_once_with(combined)
    sort.assert_called_once_with(deduped)
    save_report_info.assert_called_once_with(ordered, json_path)
    report_gen.generate_reports.assert_called_once_with(ordered)

    assert not json_path.exists()


def test_close_rerun_persistence_errors_are_swallowed(listener: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    internals = _get_internals(listener)
    cfg = internals["cfg"]
    state = internals["state"]

    cfg.is_rerun_activated = True
    state.report_info = [{"dummy": "info"}]

    from SelfhealingAgents.self_healing_system.reports.report_info_persistence import REPORT_INFO_FILE
    json_path = Path.cwd() / REPORT_INFO_FILE.name
    if json_path.exists():
        json_path.unlink()

    original_exists = Path.exists

    def boom_exists(self: Path) -> bool:  # type: ignore[override]
        if self.name == REPORT_INFO_FILE.name:
            raise RuntimeError("exists failed")
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", boom_exists, raising=True)

    try:
        listener.close()
    except Exception:
        pytest.fail("Exception from persistence logic should be swallowed in close() with rerun")