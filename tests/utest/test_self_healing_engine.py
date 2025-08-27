import sys
import types
import pytest
from unittest.mock import MagicMock, patch

from SelfhealingAgents.self_healing_system.self_healing_engine import SelfHealingEngine


@pytest.fixture
def listener_state():
    mock_cfg = MagicMock()
    mock_cfg.enable_self_healing = True
    mock_cfg.max_retries = 2
    state = MagicMock()
    state.cfg = mock_cfg
    state.context = {}
    state.healed = False
    state.retry_count = 0
    state.should_generate_locators = True
    state.suggestions = ["locator1", "locator2"]
    state.tried_locators = []
    state.report_info = []
    return state


@pytest.fixture
def engine(listener_state):
    return SelfHealingEngine(listener_state)


def test_start_test_sets_context_and_logs(engine, listener_state):
    data = MagicMock()
    data.name = "TestName"
    result_ = MagicMock()
    engine.start_test(data, result_)
    assert listener_state.context["current_test"] == "TestName"


def test_start_test_does_nothing_if_healing_disabled(engine, listener_state):
    listener_state.cfg.enable_self_healing = False
    data = MagicMock()
    result_ = MagicMock()
    engine.start_test(data, result_)
    assert "current_test" not in listener_state.context


def test_end_test_logs_on_failure(engine, listener_state):
    data = MagicMock()
    data.name = "TestName"
    result_ = MagicMock()
    result_.failed = True
    engine.end_test(data, result_)


def test_end_test_does_nothing_if_healing_disabled(engine, listener_state):
    listener_state.cfg.enable_self_healing = False
    data = MagicMock()
    result_ = MagicMock()
    result_.failed = True
    engine.end_test(data, result_)


def test_initiate_healing_locator_response(monkeypatch, engine, listener_state):
    from SelfhealingAgents.self_healing_system.schemas.api.locator_healing import LocatorHealingResponse
    import SelfhealingAgents.self_healing_system.self_healing_engine as she
    she.LocatorHealingResponse = LocatorHealingResponse

    def fake_kickoff_healing(*args, **kwargs):
        return LocatorHealingResponse(suggestions=["foo", "bar"])

    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.self_healing_engine.KickoffMultiAgentSystem.kickoff_healing",
        fake_kickoff_healing
    )

    listener_state.suggestions = []
    listener_state.should_generate_locators = True
    listener_state.retry_count = 0

    engine._initiate_healing(MagicMock())
    assert listener_state.suggestions == ["foo", "bar"]
    assert listener_state.should_generate_locators is False
    assert listener_state.retry_count == 1


def test_initiate_healing_no_healing_needed(monkeypatch, engine, listener_state):
    try:
        from SelfhealingAgents.self_healing_system.schemas.api.locator_healing import NoHealingNeededResponse
    except Exception:
        mod_name = "SelfhealingAgents.self_healing_system.schemas.api.locator_healing"
        mod = sys.modules.get(mod_name) or types.ModuleType(mod_name)
        class NoHealingNeededResponse:
            def __init__(self, message: str) -> None:
                self.message = message
        mod.NoHealingNeededResponse = NoHealingNeededResponse
        sys.modules[mod_name] = mod
        from SelfhealingAgents.self_healing_system.schemas.api.locator_healing import NoHealingNeededResponse

    import SelfhealingAgents.self_healing_system.self_healing_engine as she
    she.NoHealingNeededResponse = NoHealingNeededResponse

    def fake_kickoff_healing(*args, **kwargs):
        return NoHealingNeededResponse(message="test")

    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.self_healing_engine.KickoffMultiAgentSystem.kickoff_healing",
        fake_kickoff_healing
    )

    listener_state.suggestions = ["foo"]
    listener_state.should_generate_locators = False

    engine._initiate_healing(MagicMock())
    assert listener_state.suggestions is None
    assert listener_state.should_generate_locators is True


def test_try_locator_suggestions_success(engine, listener_state):
    data = MagicMock()
    with patch.object(engine, "_rerun_keyword_with_suggested_locator", return_value="result"):
        result = engine._try_locator_suggestions(data)
    assert result == "result"
    assert listener_state.tried_locators == ["locator1"]
    assert listener_state.healed is True
    assert listener_state.suggestions == ["locator2"]


def test_try_locator_suggestions_empty(engine, listener_state):
    listener_state.suggestions = []
    data = MagicMock()
    result = engine._try_locator_suggestions(data)
    assert result is None


def test_try_locator_suggestions_index_error(engine, listener_state):
    listener_state.suggestions = []
    data = MagicMock()
    result = engine._try_locator_suggestions(data)
    assert result is None


@patch("SelfhealingAgents.self_healing_system.self_healing_engine.BuiltIn")
def test_rerun_keyword_with_suggested_locator_success(mock_built_in, engine):
    data = MagicMock()
    data.name = "Keyword"
    data.args = ["old_locator", "arg2"]
    mock_built_in().run_keyword.return_value = "return_value"
    result = engine._rerun_keyword_with_suggested_locator(data, suggested_locator="new_locator")
    assert data.args[0] == "new_locator"
    assert result == "return_value"


@patch("SelfhealingAgents.self_healing_system.self_healing_engine.BuiltIn")
def test_rerun_keyword_with_suggested_locator_no_locator(mock_built_in, engine):
    data = MagicMock()
    data.args = ["locator"]
    result = engine._rerun_keyword_with_suggested_locator(data, suggested_locator=None)
    assert result is None


@patch("SelfhealingAgents.self_healing_system.self_healing_engine.BuiltIn")
def test_rerun_keyword_with_suggested_locator_exception(mock_built_in, engine):
    data = MagicMock()
    data.name = "Keyword"
    data.args = ["locator"]
    mock_built_in().run_keyword.side_effect = Exception("fail")
    with pytest.raises(Exception):
        engine._rerun_keyword_with_suggested_locator(data, suggested_locator="locator")


@patch("SelfhealingAgents.self_healing_system.self_healing_engine.BuiltIn")
def test_record_report_appends_report_data(mock_built_in, engine, listener_state):
    data = MagicMock()
    data.args = ["failed_locator"]
    data.source = MagicMock()
    data.source.parts = ["file.robot"]
    data.parent.name = "TestName"
    data.name = "Keyword"
    data.lineno = 42
    mock_built_in().replace_variables.return_value = "failed_locator"
    listener_state.tried_locators = ["locator1", "locator2"]
    listener_state.report_info = []
    engine._record_report(data, healed_locator="healed_locator", status="PASS")
    assert len(listener_state.report_info) == 1
    report = listener_state.report_info[0]
    assert report.file == "file.robot"
    assert report.test_name == "TestName"
    assert report.failed_locator == "failed_locator"
    assert report.healed_locator == "healed_locator"
    assert report.tried_locators == ["locator1", "locator2"]


def test_reset_state_clears_state(engine, listener_state):
    listener_state.retry_count = 5
    listener_state.suggestions = ["foo"]
    listener_state.should_generate_locators = False
    listener_state.tried_locators = ["a", "b"]
    engine._reset_state()
    assert listener_state.retry_count == 0
    assert listener_state.suggestions is None
    assert listener_state.should_generate_locators is True
    assert listener_state.tried_locators == []
