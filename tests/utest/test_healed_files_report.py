from __future__ import annotations

import types
import pytest
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Iterable, List, Tuple

from SelfhealingAgents.self_healing_system.reports.report_types.healed_files_report import HealedFilesReport
from SelfhealingAgents.self_healing_system.schemas.internal_state.report_context import ReportContext
from SelfhealingAgents.self_healing_system.schemas.internal_state.locator_replacements import LocatorReplacements


@dataclass
class _ReportDataStub:
    file: str
    test_name: str
    locator_origin: str
    failed_locator: str
    healed_locator: str
    keyword_source: str
    keyword_args: list[str] | None = None


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
    def __init__(self, name: str, value: Iterable[str] | None = None) -> None:
        self.name: str = name
        self.value: Tuple[str, ...] = tuple(value or [])
        arguments = list(self.value or [""])
        self.tokens = [
            types.SimpleNamespace(value=name, type="VARIABLE"),
            types.SimpleNamespace(value="    ", type="SEPARATOR"),
            *[types.SimpleNamespace(value=arg, type="ARGUMENT") for arg in arguments],
            types.SimpleNamespace(value="\n", type="EOL"),
        ]


class _FakeVariableSection:
    def __init__(self, body: List[_FakeVariable]) -> None:
        self.body: List[_FakeVariable] = body


class _FakeKeyword:
    def __init__(self, name: str) -> None:
        self.name: str = name
        self.visits: List[Tuple[str, List[Tuple[str, str]]]] = []


class _FakeKeywordSection:
    def __init__(self, body: List[Any]) -> None:
        self.body: List[Any] = body


class _FakeTestCase:
    def __init__(self, name: str) -> None:
        self.name: str = name
        self.visits: List[Tuple[str, List[Tuple[str, str]]]] = []


class _FakeTestCaseSection:
    def __init__(self, body: List[Any]) -> None:
        self.body: List[Any] = body


class _FakeComment:
    def __init__(self) -> None:
        self.visits: List[Tuple[str, List[Tuple[str, str]]]] = []


class _RecorderVisitor:
    def __init__(self, kind: str, replacements: List[Any], variable_updates: dict[str, str] | None = None) -> None:
        self.kind: str = kind
        self.replacements: List[Any] = replacements
        self.variable_updates: dict[str, str] = variable_updates or {}

    def visit(self, model: _FakeFile) -> None:
        model.visits.append((self.kind, self.replacements))


@pytest.fixture
def module_under_test(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    import SelfhealingAgents.self_healing_system.reports.report_types.healed_files_report as mod

    monkeypatch.setattr(mod, "File", _FakeFile, raising=True)
    monkeypatch.setattr(mod, "SettingSection", _FakeSettingSection, raising=True)
    monkeypatch.setattr(mod, "ResourceImport", _FakeResourceImport, raising=True)
    monkeypatch.setattr(mod, "VariableSection", _FakeVariableSection, raising=True)
    monkeypatch.setattr(mod, "TestCaseSection", _FakeTestCaseSection, raising=True)
    monkeypatch.setattr(mod, "KeywordSection", _FakeKeywordSection, raising=True)

    def locator_replacer_factory(replacements: List[Any]) -> _RecorderVisitor:
        fake_updates = {}
        for repl in replacements:
            if hasattr(repl, "failed_locator"):
                fake_updates[repl.failed_locator] = getattr(repl, "healed_locator", "")
        return _RecorderVisitor("locator", replacements, fake_updates)

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
            test_name="Test",
            locator_origin="Test",
            failed_locator="old1",
            healed_locator="new1",
            keyword_source=str(suite_path),
        ),
        _ReportDataStub(
            file="res",
            test_name="Test",
            locator_origin="Test",
            failed_locator="old2",
            healed_locator="new2",
            keyword_source=str(suite_path),
        ),
    ]

    replacements = module_under_test.HealedFilesReport._get_replacements_for_file(
        report_info=report_info, source_path=suite_path
    )

    assert "old1" == replacements[0].failed_locator
    assert "new1" == replacements[0].healed_locator

    assert "old2" == replacements[1].failed_locator
    assert "new2" == replacements[1].healed_locator

    assert len(replacements) == 2


def test_get_replacements_handles_oserror_and_returns_direct_entries_only(
    module_under_test: types.ModuleType,
    tmp_suite_paths: dict[str, Path],
) -> None:
    suite_path = tmp_suite_paths["suite"]

    report_info: List[_ReportDataStub] = [
        _ReportDataStub(
            file=suite_path.name,
            test_name="Test",
            locator_origin="Test",
            failed_locator="old",
            healed_locator="new",
            keyword_source=str(suite_path),
        )
    ]

    def _raising_get_model(_: str) -> None:
        raise OSError("cannot open")

    pytest.monkeypatch = None
    import SelfhealingAgents.self_healing_system.reports.report_types.healed_files_report as mod
    orig = mod.get_model
    try:
        object.__setattr__(mod, "get_model", _raising_get_model)
        replacements = mod.HealedFilesReport._get_replacements_for_file(
            report_info=report_info, source_path=suite_path
        )
    finally:
        object.__setattr__(mod, "get_model", orig)

    assert replacements == [LocatorReplacements(test_case='Test', locator_origin='Test',
                                                failed_locator='old', healed_locator='new')]


def test_replace_in_common_model_applies_visitors_and_saves(
    module_under_test: types.ModuleType,
    fake_models: dict[str, _FakeFile],
    tmp_suite_paths: dict[str, Path],
    tmp_path: Path,
) -> None:
    suite_path = tmp_suite_paths["suite"]
    test_cases = [_FakeTestCase(name=f"Test{i}") for i in range(1, 4)]
    test_section = module_under_test.TestCaseSection(body=test_cases)
    fake_models[str(suite_path)] = _FakeFile(sections=[test_section])

    report = HealedFilesReport(base_dir=tmp_path)
    replacements: List[LocatorReplacements] = [
        LocatorReplacements(test_case="Test1", locator_origin="Test1", failed_locator="a", healed_locator="b"),
        LocatorReplacements(test_case="Test2", locator_origin="Test2", failed_locator="c", healed_locator="d"),
        LocatorReplacements(test_case="Test3", locator_origin="Test3", failed_locator="e", healed_locator="f"),
    ]

    report._replace_in_common_model(source_path=suite_path, replacements=replacements)

    out_dir = tmp_path / "healed_files" / suite_path.parent.name
    out_file = out_dir / suite_path.name
    assert out_file.exists()
    model = fake_models[str(suite_path)]
    for case in test_cases:
        assert case.visits and case.visits[0][0] == "locator"
    assert model.visits
    assert model.visits[-1][0] == "variables"
    assert len(model.visits[-1][1]) == len(replacements)
    assert model.saved_to == out_file


def test_replace_in_common_model_skips_comment_entries(
    module_under_test: types.ModuleType,
    fake_models: dict[str, _FakeFile],
    tmp_suite_paths: dict[str, Path],
    tmp_path: Path,
) -> None:
    suite_path = tmp_suite_paths["suite"]
    comment = _FakeComment()
    keyword = _FakeKeyword(name="Reusable Keyword")
    keyword_section = module_under_test.KeywordSection(body=[comment, keyword])
    fake_models[str(suite_path)] = _FakeFile(sections=[keyword_section])

    report = HealedFilesReport(base_dir=tmp_path)
    replacements: List[LocatorReplacements] = [
        LocatorReplacements(
            test_case="",
            locator_origin="Reusable Keyword",
            failed_locator="old",
            healed_locator="new",
        )
    ]

    report._replace_in_common_model(source_path=suite_path, replacements=replacements)

    assert keyword.visits == [("locator", replacements)]
    assert comment.visits == []


def test_replace_in_common_model_raises_runtime_error_on_save_failure(
    module_under_test: types.ModuleType,
    fake_models: dict[str, _FakeFile],
    tmp_suite_paths: dict[str, Path],
    tmp_path: Path,
) -> None:
    suite_path = tmp_suite_paths["suite"]
    fake_models[str(suite_path)] = _FakeFile(sections=[], should_fail_save=True)

    report = HealedFilesReport(base_dir=tmp_path)

    replacements = [
        LocatorReplacements(test_case="TestX", locator_origin="TestX", failed_locator="x", healed_locator="y"),
    ]

    with pytest.raises(RuntimeError) as exc:
        report._replace_in_common_model(source_path=suite_path, replacements=replacements)

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

    var_section = _FakeVariableSection(
        body=[
            _FakeVariable(name="${LOC}", value=["old-loc"]),
            _FakeVariable(name="${OTHER}", value=["other"]),
        ]
    )
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

    replacements = [
        LocatorReplacements(test_case="", locator_origin="", failed_locator="${LOC}", healed_locator="${HEALED}")
    ]
    variable_updates = {"${LOC}": "${HEALED}"}

    report._replace_in_resource_model(
        source_path=suite_path,
        replacements=replacements,
        report_context=ctx,
        variable_updates=variable_updates,
    )

    out_dir = tmp_path / "healed_files" / suite_path.parent.name
    out_file = out_dir / resource_path.name
    assert out_file.exists()
    assert resource_model.visits == [
        ("variables", [("${LOC}", "${HEALED}")])
    ]
    assert ctx.external_resource_paths == [suites_side_alias]

    fake_models[str(out_file)] = _FakeFile(sections=[var_section])
    out_file.touch()
    report._replace_in_resource_model(
        source_path=suite_path,
        replacements=replacements,
        report_context=ctx,
        variable_updates=variable_updates,
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

    var_section = _FakeVariableSection(body=[_FakeVariable(name="${NOT_ME}", value=["noop"])])
    res_model = _FakeFile(sections=[var_section])
    fake_models[str(resource_path)] = res_model
    fake_models[str(tmp_suite_paths["suites_dir"] / resource_path.name)] = res_model

    report = HealedFilesReport(base_dir=tmp_path)
    ctx = ReportContext(report_info=[])

    replacements = [
        LocatorReplacements(test_case="", locator_origin="", failed_locator="${LOCATOR}", healed_locator="${NEW}")
    ]
    variable_updates = {}

    report._replace_in_resource_model(
        source_path=suite_path,
        replacements=replacements,
        report_context=ctx,
        variable_updates=variable_updates,
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
        source_path=tmp_suite_paths["suite"],
        replacements=[],
        report_context=ctx,
        variable_updates={},
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

    def _common(self: HealedFilesReport, source_path: Path, replacements: list) -> dict[str, str]:
        # replacements should be a list of LocatorReplacements objects
        assert all(isinstance(r, LocatorReplacements) for r in replacements)
        calls_common.append(source_path)
        return {"${FAKE}": "value"}

    def _resource(
        self: HealedFilesReport,
        source_path: Path,
        replacements: list,
        report_context: ReportContext,
        variable_updates: dict[str, str],
    ) -> None:
        # replacements should be a list of LocatorReplacements objects
        assert all(isinstance(r, LocatorReplacements) for r in replacements)
        assert variable_updates == {"${FAKE}": "value"}
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
                "locator_origin": "T",
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
                "locator_origin": "T2",
                "tried_locators": [],
            },
        ]
    )

    report = HealedFilesReport(base_dir=tmp_path)
    result_ctx = report._generate_report(ctx)

    assert result_ctx is ctx
    assert calls_common == [Path(str(suite_path))]
    assert calls_resource == [Path(str(suite_path))]
