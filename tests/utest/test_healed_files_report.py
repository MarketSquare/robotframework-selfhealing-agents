from __future__ import annotations

import types
import pytest
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Iterable, List, Tuple

from RobotAid.self_healing_system.reports.report_types.healed_files_report import HealedFilesReport
from RobotAid.self_healing_system.schemas.internal_state.report_context import ReportContext


@dataclass
class _ReportDataStub:
    file: str
    failed_locator: str
    healed_locator: str
    keyword_source: str


class _FakeFile:
    def __init__(self, sections: List[object] | None = None, should_fail_save: bool = False) -> None:
        self.sections: List[object] = sections or []
        self._should_fail_save: bool = should_fail_save
        self.saved_to: Path | None = None
        self.visits: List[Tuple[str, List[Tuple[str, str]]]] = []

    def save(self, path: str) -> None:
        if self._should_fail_save:
            raise OSError("simulated save error")
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text("# fake healed file\n")
        self.saved_to = p


class _FakeSettingSection:
    def __init__(self, body: List[Any]) -> None:
        self.body: List[Any] = body


class _FakeResourceImport:
    def __init__(self, name: str) -> None:
        self.name: str = name


class _FakeVariable:
    def __init__(self, value: Iterable[str]) -> None:
        self.value: Tuple[str, ...] = tuple(value)


class _FakeVariableSection:
    def __init__(self, body: List[_FakeVariable]) -> None:
        self.body: List[_FakeVariable] = body


class _RecorderVisitor:
    def __init__(self, kind: str, replacements: List[Tuple[str, str]]) -> None:
        self.kind: str = kind
        self.replacements: List[Tuple[str, str]] = replacements

    def visit(self, model: _FakeFile) -> None:
        model.visits.append((self.kind, self.replacements))


@pytest.fixture
def module_under_test(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    import RobotAid.self_healing_system.reports.report_types.healed_files_report as mod

    monkeypatch.setattr(mod, "File", _FakeFile, raising=True)
    monkeypatch.setattr(mod, "SettingSection", _FakeSettingSection, raising=True)
    monkeypatch.setattr(mod, "ResourceImport", _FakeResourceImport, raising=True)
    monkeypatch.setattr(mod, "VariableSection", _FakeVariableSection, raising=True)

    def locator_replacer_factory(replacements: List[Tuple[str, str]]) -> _RecorderVisitor:
        return _RecorderVisitor("locator", replacements)

    def variables_replacer_factory(replacements: List[Tuple[str, str]]) -> _RecorderVisitor:
        return _RecorderVisitor("variables", replacements)

    monkeypatch.setattr(mod, "LocatorReplacer", locator_replacer_factory, raising=True)
    monkeypatch.setattr(mod, "VariablesReplacer", variables_replacer_factory, raising=True)

    return mod


@pytest.fixture
def fake_models(monkeypatch: pytest.MonkeyPatch, module_under_test: types.ModuleType) -> dict[str, _FakeFile]:
    models: dict[str | Path, _FakeFile] = {}

    def _get_model(path: str | Path) -> _FakeFile:
        key = str(path)
        if key not in models:
            raise OSError(f"no model for path={path}")
        return models[key]

    def _get_resource_model(path: str | Path) -> _FakeFile:
        key = str(path)
        if key not in models:
            raise OSError(f"no resource model for path={path}")
        return models[key]

    monkeypatch.setattr(module_under_test, "get_model", _get_model, raising=True)
    monkeypatch.setattr(module_under_test, "get_resource_model", _get_resource_model, raising=True)

    return models


@pytest.fixture
def tmp_suite_paths(tmp_path: Path) -> dict[str, Path]:
    base = tmp_path / "project"
    suites_dir = base / "suites"
    resources_dir = base / "resources"
    suites_dir.mkdir(parents=True)
    resources_dir.mkdir(parents=True)
    return {
        "base": base,
        "suite": suites_dir / "suite.robot",
        "resource": resources_dir / "res.resource",
        "resources_dir": resources_dir,
        "suites_dir": suites_dir,
    }


def test_get_replacements_includes_resource_entries(
    module_under_test: types.ModuleType,
    fake_models: dict[str, _FakeFile],
    tmp_suite_paths: dict[str, Path],
) -> None:
    suite_path = tmp_suite_paths["suite"]
    resource_path = tmp_suite_paths["resource"]

    setting = _FakeSettingSection([_FakeResourceImport(name=str(resource_path.name))])
    model = _FakeFile(sections=[setting])
    fake_models[str(suite_path)] = model

    report_info: List[_ReportDataStub] = [
        _ReportDataStub(
            file=suite_path.name,
            failed_locator="old1",
            healed_locator="new1",
            keyword_source=str(suite_path),
        ),
        _ReportDataStub(
            file="res",
            failed_locator="old2",
            healed_locator="new2",
            keyword_source=str(suite_path),
        ),
    ]

    replacements = module_under_test.HealedFilesReport._get_replacements_for_file(
        report_info=report_info, source_path=suite_path
    )

    assert ("old1", "new1") in replacements
    assert ("old2", "new2") in replacements
    assert len(replacements) == 2


def test_get_replacements_handles_oserror_and_returns_direct_entries_only(
    module_under_test: types.ModuleType,
    tmp_suite_paths: dict[str, Path],
) -> None:
    suite_path = tmp_suite_paths["suite"]

    report_info: List[_ReportDataStub] = [
        _ReportDataStub(
            file=suite_path.name,
            failed_locator="old",
            healed_locator="new",
            keyword_source=str(suite_path),
        )
    ]

    def _raising_get_model(_: str) -> None:
        raise OSError("cannot open")

    pytest.monkeypatch = None
    import RobotAid.self_healing_system.reports.report_types.healed_files_report as mod
    orig = mod.get_model
    try:
        object.__setattr__(mod, "get_model", _raising_get_model)
        replacements = mod.HealedFilesReport._get_replacements_for_file(
            report_info=report_info, source_path=suite_path
        )
    finally:
        object.__setattr__(mod, "get_model", orig)

    assert replacements == [("old", "new")]


def test_replace_in_common_model_applies_visitors_and_saves(
    module_under_test: types.ModuleType,
    fake_models: dict[str, _FakeFile],
    tmp_suite_paths: dict[str, Path],
    tmp_path: Path,
) -> None:
    suite_path = tmp_suite_paths["suite"]
    fake_models[str(suite_path)] = _FakeFile(sections=[])

    report = HealedFilesReport(base_dir=tmp_path)
    replacements: List[Tuple[str, str]] = [("a", "b"), ("c", "d")]

    report._replace_in_common_model(source_path=suite_path, replacements=replacements)

    out_dir = tmp_path / "healed_files" / suite_path.parent.name
    out_file = out_dir / suite_path.name
    assert out_file.exists()
    model = fake_models[str(suite_path)]
    assert model.visits == [("locator", replacements), ("variables", replacements)]
    assert model.saved_to == out_file


def test_replace_in_common_model_raises_runtime_error_on_save_failure(
    module_under_test: types.ModuleType,
    fake_models: dict[str, _FakeFile],
    tmp_suite_paths: dict[str, Path],
    tmp_path: Path,
) -> None:
    suite_path = tmp_suite_paths["suite"]
    fake_models[str(suite_path)] = _FakeFile(sections=[], should_fail_save=True)

    report = HealedFilesReport(base_dir=tmp_path)

    with pytest.raises(RuntimeError) as exc:
        report._replace_in_common_model(source_path=suite_path, replacements=[("x", "y")])

    assert "Failed to save healed test suite" in str(exc.value)


def test_replace_in_resource_model_applies_when_defined_and_appends_path(
    module_under_test: types.ModuleType,
    fake_models: dict[str, _FakeFile],
    tmp_suite_paths: dict[str, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suite_path = tmp_suite_paths["suite"]
    resource_path = tmp_suite_paths["resource"]

    setting = _FakeSettingSection([_FakeResourceImport(name=str(resource_path.name))])
    suite_model = _FakeFile(sections=[setting])
    fake_models[str(suite_path)] = suite_model

    var_section = _FakeVariableSection(body=[_FakeVariable(value=["${LOC}", "${OTHER}"])])
    resource_model = _FakeFile(sections=[var_section])
    fake_models[str(resource_path)] = resource_model

    suites_side_alias = tmp_suite_paths["suites_dir"] / resource_path.name
    fake_models[str(suites_side_alias)] = resource_model

    get_resource_calls: List[str] = []

    def _tracking_get_resource(path: str | Path) -> _FakeFile:
        get_resource_calls.append(str(path))
        return fake_models[str(path)]

    monkeypatch.setattr(module_under_test, "get_resource_model", _tracking_get_resource, raising=True)

    report = HealedFilesReport(base_dir=tmp_path)
    ctx = ReportContext(
        report_info=[],
        external_resource_paths=[],
    )

    report._replace_in_resource_model(
        source_path=suite_path,
        replacements=[("${LOC}", "${HEALED}")],
        report_context=ctx,
    )

    out_dir = tmp_path / "healed_files" / suite_path.parent.name
    out_file = out_dir / resource_path.name
    assert out_file.exists()
    assert resource_model.visits == [("variables", [("${LOC}", "${HEALED}")])]
    assert ctx.external_resource_paths == [suites_side_alias]

    fake_models[str(out_file)] = _FakeFile(sections=[var_section])
    out_file.touch()
    report._replace_in_resource_model(
        source_path=suite_path,
        replacements=[("${LOC}", "${HEALED}")],
        report_context=ctx,
    )
    assert any(str(out_file) == c for c in get_resource_calls)


def test_replace_in_resource_model_ignores_when_no_matching_defined_vars(
    module_under_test: types.ModuleType,
    fake_models: dict[str, _FakeFile],
    tmp_suite_paths: dict[str, Path],
    tmp_path: Path,
) -> None:
    suite_path = tmp_suite_paths["suite"]
    resource_path = tmp_suite_paths["resource"]

    setting = _FakeSettingSection([_FakeResourceImport(name=str(resource_path.name))])
    suite_model = _FakeFile(sections=[setting])
    fake_models[str(suite_path)] = suite_model

    var_section = _FakeVariableSection(body=[_FakeVariable(value=["${NOT_ME}"])])
    res_model = _FakeFile(sections=[var_section])
    fake_models[str(resource_path)] = res_model
    fake_models[str(tmp_suite_paths["suites_dir"] / resource_path.name)] = res_model

    report = HealedFilesReport(base_dir=tmp_path)
    ctx = ReportContext(report_info=[])

    report._replace_in_resource_model(
        source_path=suite_path,
        replacements=[("${LOCATOR}", "${NEW}")],
        report_context=ctx,
    )

    out_dir = tmp_path / "healed_files" / suite_path.parent.name
    out_file = out_dir / resource_path.name
    assert not out_file.exists()
    assert ctx.external_resource_paths == []


def test_replace_in_resource_model_swallows_errors(
    module_under_test: types.ModuleType,
    tmp_suite_paths: dict[str, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_get_model(_: str) -> None:
        raise OSError("boom")

    monkeypatch.setattr(module_under_test, "get_model", _raise_get_model, raising=True)

    report = HealedFilesReport(base_dir=tmp_path)
    ctx = ReportContext(report_info=[])

    report._replace_in_resource_model(
        source_path=tmp_suite_paths["suite"], replacements=[], report_context=ctx
    )

    assert ctx.external_resource_paths == []


def test_generate_report_deduplicates_sources_and_calls_children(
    module_under_test: types.ModuleType,
    fake_models: dict[str, _FakeFile],
    tmp_path: Path,
    tmp_suite_paths: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suite_path = tmp_suite_paths["suite"]
    other_path = tmp_suite_paths["suites_dir"] / "another.robot"

    fake_models[str(suite_path)] = _FakeFile(sections=[_FakeSettingSection([])])

    calls_common: List[Path] = []
    calls_resource: List[Path] = []

    def _common(self: HealedFilesReport, source_path: Path, replacements: List[Tuple[str, str]]) -> None:
        calls_common.append(source_path)

    def _resource(
        self: HealedFilesReport,
        source_path: Path,
        replacements: List[Tuple[str, str]],
        report_context: ReportContext,
    ) -> None:
        calls_resource.append(source_path)

    monkeypatch.setattr(HealedFilesReport, "_replace_in_common_model", _common, raising=True)
    monkeypatch.setattr(HealedFilesReport, "_replace_in_resource_model", _resource, raising=True)

    ctx = ReportContext(
        report_info=[
            {
                "file": suite_path.name,
                "keyword_source": str(suite_path),
                "test_name": "T",
                "keyword": "K",
                "keyword_args": [],
                "lineno": 1,
                "failed_locator": "a",
                "healed_locator": "b",
                "tried_locators": [],
            },
            {
                "file": other_path.name,
                "keyword_source": str(suite_path),
                "test_name": "T2",
                "keyword": "K2",
                "keyword_args": [],
                "lineno": 2,
                "failed_locator": "c",
                "healed_locator": "d",
                "tried_locators": [],
            },
        ]
    )

    report = HealedFilesReport(base_dir=tmp_path)
    result_ctx = report._generate_report(ctx)

    assert result_ctx is ctx
    assert calls_common == [Path(str(suite_path))]
    assert calls_resource == [Path(str(suite_path))]
