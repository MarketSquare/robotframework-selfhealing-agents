import pytest
from unittest.mock import MagicMock

import SelfhealingAgents.self_healing_system.reports.report_generator as report_generator
from SelfhealingAgents.self_healing_system.reports.report_generator import ReportGenerator
from SelfhealingAgents.self_healing_system.schemas.internal_state.report_data import ReportData


@pytest.fixture
def dummy_report_data():
    return [ReportData(
        file='dummy.robot',
        keyword_source='test.robot',
        test_name='TestCase',
        keyword='Click Element',
        keyword_args=['arg1', 'arg2'],
        lineno=42,
        failed_locator='//button[@id="old"]',
        healed_locator='//button[@id="new"]',
        tried_locators=['//button[@id="old"]', '//button[@id="alt"]']
    )]

@pytest.fixture
def patch_workspace(monkeypatch, tmp_path):
    fake_file = tmp_path / "a" / "b" / "c" / "d" / "report_generator.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("# dummy")
    monkeypatch.setattr("SelfhealingAgents.self_healing_system.reports.report_generator.__file__", str(fake_file))
    return tmp_path

def test_init_creates_clean_reports_dir(patch_workspace, monkeypatch):
    reports_dir = patch_workspace / "reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "oldfile.txt").write_text("old")

    monkeypatch.setattr("SelfhealingAgents.self_healing_system.reports.report_types.action_log_report.ActionLogReport",
                        MagicMock())
    monkeypatch.setattr("SelfhealingAgents.self_healing_system.reports.report_types.healed_files_report.HealedFilesReport",
                        MagicMock())
    monkeypatch.setattr("SelfhealingAgents.self_healing_system.reports.report_types.diff_files_report.DiffFilesReport",
                        MagicMock())

    rg = ReportGenerator(base_dir=reports_dir)

    assert reports_dir.exists()
    assert rg._base_dir == reports_dir
    assert not (reports_dir / "oldfile.txt").exists()

def test_init_creates_reports_dir_if_not_exists(patch_workspace, monkeypatch):
    reports_dir = patch_workspace / "reports"
    if reports_dir.exists():
        reports_dir.rmdir()

    monkeypatch.setattr("shutil.rmtree", MagicMock())
    monkeypatch.setattr("SelfhealingAgents.self_healing_system.reports.report_types.action_log_report.ActionLogReport",
                        MagicMock())
    monkeypatch.setattr("SelfhealingAgents.self_healing_system.reports.report_types.healed_files_report.HealedFilesReport",
                        MagicMock())
    monkeypatch.setattr("SelfhealingAgents.self_healing_system.reports.report_types.diff_files_report.DiffFilesReport",
                        MagicMock())

    rg = ReportGenerator(base_dir=reports_dir)
    assert reports_dir.exists()

def test_generate_reports_calls_all_report_types(monkeypatch, patch_workspace, dummy_report_data) -> None:
    mock_action: MagicMock = MagicMock()
    mock_healed: MagicMock = MagicMock()
    mock_diff: MagicMock = MagicMock()
    dummy_ctx: MagicMock = MagicMock()
    monkeypatch.setattr(report_generator, "ActionLogReport", lambda base_dir: mock_action, raising=True)
    monkeypatch.setattr(report_generator, "HealedFilesReport", lambda base_dir: mock_healed, raising=True)
    monkeypatch.setattr(report_generator, "DiffFilesReport", lambda base_dir: mock_diff, raising=True)
    monkeypatch.setattr(report_generator, "ReportContext", lambda report_info: dummy_ctx, raising=True)

    rg: ReportGenerator = ReportGenerator()

    mock_action.generate_report.return_value = dummy_ctx
    mock_healed.generate_report.return_value = dummy_ctx
    mock_diff.generate_report.return_value = dummy_ctx

    rg.generate_reports(dummy_report_data)

    mock_action.generate_report.assert_called_once_with(dummy_ctx)
    mock_healed.generate_report.assert_called_once_with(dummy_ctx)
    mock_diff.generate_report.assert_called_once_with(dummy_ctx)

def test_generate_reports_with_empty_data(monkeypatch, patch_workspace):
    mock_action = MagicMock()
    mock_healed = MagicMock()
    mock_diff = MagicMock()
    monkeypatch.setattr(report_generator, "ActionLogReport", lambda base_dir: mock_action, raising=True)
    monkeypatch.setattr(report_generator, "HealedFilesReport", lambda base_dir: mock_healed, raising=True)
    monkeypatch.setattr(report_generator, "DiffFilesReport", lambda base_dir: mock_diff, raising=True)

    rg = ReportGenerator()

    from SelfhealingAgents.self_healing_system.schemas.internal_state import report_context
    dummy_ctx = MagicMock()
    monkeypatch.setattr(report_context, "ReportContext", lambda report_info: dummy_ctx)

    mock_action.generate_report.return_value = dummy_ctx
    mock_healed.generate_report.return_value = dummy_ctx
    mock_diff.generate_report.return_value = dummy_ctx

    rg.generate_reports([])

    mock_action.generate_report.assert_called_once()
    mock_healed.generate_report.assert_called_once()
    mock_diff.generate_report.assert_called_once()

def test_generate_reports_propagates_exceptions(monkeypatch, patch_workspace, dummy_report_data):
    mock_action = MagicMock()
    mock_healed = MagicMock()
    mock_diff = MagicMock()
    monkeypatch.setattr(report_generator, "ActionLogReport", lambda base_dir: mock_action, raising=True)
    monkeypatch.setattr(report_generator, "HealedFilesReport", lambda base_dir: mock_healed, raising=True)
    monkeypatch.setattr(report_generator, "DiffFilesReport", lambda base_dir: mock_diff, raising=True)

    rg = ReportGenerator()

    from SelfhealingAgents.self_healing_system.schemas.internal_state import report_context
    dummy_ctx = MagicMock()
    monkeypatch.setattr(report_context, "ReportContext", lambda report_info: dummy_ctx)

    mock_action.generate_report.side_effect = RuntimeError("fail")

    with pytest.raises(RuntimeError, match="fail"):
        rg.generate_reports(dummy_report_data)
    mock_action.generate_report.assert_called_once()
    mock_healed.generate_report.assert_not_called()
    mock_diff.generate_report.assert_not_called()