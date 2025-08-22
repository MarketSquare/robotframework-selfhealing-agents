import re
import pytest
from pathlib import Path
from typing import List

from RobotAid.self_healing_system.schemas.internal_state.report_context import (
    ReportContext,
)
from RobotAid.self_healing_system.schemas.internal_state.report_data import ReportData
from RobotAid.self_healing_system.reports.report_types.diff_files_report import (
    DiffFilesReport,
)
import RobotAid.self_healing_system.reports.report_types.diff_files_report as diff_module


def _write(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _mk_report_context(paths: List[Path]) -> ReportContext:
    report_info = [
        ReportData(
            file=pp.name,
            keyword_source=str(pp),
            test_name="T",
            keyword="K",
            keyword_args=[],
            lineno=1,
            failed_locator="a",
            healed_locator=None,
            tried_locators=[],
        )
        for pp in paths
    ]
    return ReportContext(report_info=report_info, external_resource_paths=[])


def test_no_diff_created_when_files_identical(tmp_path: Path) -> None:
    base_dir = tmp_path
    original = base_dir / "suites" / "suite1.robot"
    healed = base_dir / "healed_files" / original.parent.name / original.name
    _write(original, "*** Test Cases ***\nCase\n    Log    x")
    _write(healed, "*** Test Cases ***\nCase\n    Log    x")

    ctx = _mk_report_context([original])
    report = DiffFilesReport(base_dir)

    returned = report._generate_report(ctx)

    assert returned is ctx
    out_dir = getattr(report, "_out_dir")
    diff_dir = out_dir / original.parent.name
    diff_path = diff_dir / f"{original.stem}_diff.html"
    assert not diff_path.exists()


def test_diff_created_and_css_injected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base_dir = tmp_path
    original = base_dir / "resources" / "res.robot"
    healed = base_dir / "healed_files" / original.parent.name / original.name
    _write(original, "*** Keywords ***\nKW\n    Log    before")
    _write(healed, "*** Keywords ***\nKW\n    Log    after")

    monkeypatch.setattr(diff_module, "DIFF_CSS", "<style>.test-css{}</style>", raising=True)

    ctx = _mk_report_context([original])
    report = DiffFilesReport(base_dir)

    report._generate_report(ctx)

    out_dir = getattr(report, "_out_dir")
    diff_path = out_dir / original.parent.name / f"{original.stem}_diff.html"
    assert diff_path.exists()
    html = diff_path.read_text(encoding="utf-8")
    assert "<style>.test-css{}</style>" in html
    assert "Original" in html
    assert "Healed" in html

    plain = re.sub(r"<[^>]+>", "", html).replace("&nbsp;", " ")
    assert "before" in plain or "after" in plain


def test_union_of_sources_and_external_resources(tmp_path: Path) -> None:
    base_dir = tmp_path

    a = base_dir / "suiteA" / "a.robot"
    b = base_dir / "suiteB" / "b.robot"
    c = base_dir / "suiteC" / "c.robot"

    _write(a, "A1")
    _write(b, "B1")
    _write(c, "C1")

    _write(base_dir / "healed_files" / a.parent.name / a.name, "A2")
    _write(base_dir / "healed_files" / b.parent.name / b.name, "B1")
    _write(base_dir / "healed_files" / c.parent.name / c.name, "C2")

    ctx = ReportContext(
        report_info=[
            ReportData(
                file=a.name,
                keyword_source=str(a),
                test_name="t",
                keyword="k",
                keyword_args=[],
                lineno=1,
                failed_locator="f",
                healed_locator=None,
                tried_locators=[],
            ),
            ReportData(
                file=a.name,
                keyword_source=str(a),
                test_name="t",
                keyword="k",
                keyword_args=[],
                lineno=1,
                failed_locator="f",
                healed_locator=None,
                tried_locators=[],
            ),
        ],
        external_resource_paths=[b, c],
    )

    report = DiffFilesReport(base_dir)
    report._generate_report(ctx)

    out_dir = getattr(report, "_out_dir")
    path_a = out_dir / a.parent.name / f"{a.stem}_diff.html"
    path_b = out_dir / b.parent.name / f"{b.stem}_diff.html"
    path_c = out_dir / c.parent.name / f"{c.stem}_diff.html"

    assert path_a.exists()
    assert not path_b.exists()
    assert path_c.exists()


def test_raises_runtime_error_if_read_fails_missing_original(tmp_path: Path) -> None:
    base_dir = tmp_path
    original = base_dir / "X" / "missing.robot"
    healed = base_dir / "healed_files" / original.parent.name / original.name
    _write(healed, "content")

    ctx = _mk_report_context([original])
    report = DiffFilesReport(base_dir)

    with pytest.raises(RuntimeError) as ei:
        report._generate_report(ctx)

    msg = str(ei.value)
    assert "Failed to read files for diff" in msg
    assert str(original) in msg
    assert str(healed) in msg


def test_raises_runtime_error_if_read_fails_missing_healed(tmp_path: Path) -> None:
    base_dir = tmp_path
    original = base_dir / "X" / "present.robot"
    healed = base_dir / "healed_files" / original.parent.name / original.name
    _write(original, "content")

    ctx = _mk_report_context([original])
    report = DiffFilesReport(base_dir)

    with pytest.raises(RuntimeError) as ei:
        report._generate_report(ctx)

    msg = str(ei.value)
    assert "Failed to read files for diff" in msg
    assert str(original) in msg
    assert str(healed) in msg


def test_raises_runtime_error_if_write_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base_dir = tmp_path
    original = base_dir / "pack" / "x.robot"
    healed = base_dir / "healed_files" / original.parent.name / original.name
    _write(original, "one")
    _write(healed, "two")

    report = DiffFilesReport(base_dir)
    out_dir = getattr(report, "_out_dir")
    bad_path = out_dir / original.parent.name / f"{original.stem}_diff.html"

    def fake_write_text(self: Path, data: str, encoding: str = "utf-8") -> int:
        if self == bad_path:
            raise OSError("simulated write error")
        return Path.write_text.__wrapped__(self, data, encoding=encoding)

    monkeypatch.setattr(Path, "write_text", fake_write_text, raising=True)

    with pytest.raises(RuntimeError) as ei:
        report._generate_report(_mk_report_context([original]))

    assert "Failed to write diff file to" in str(ei.value)
    assert str(bad_path) in str(ei.value)


def test_returns_same_report_context_instance(tmp_path: Path) -> None:
    base_dir = tmp_path
    original = base_dir / "suite" / "s.robot"
    healed = base_dir / "healed_files" / original.parent.name / original.name
    _write(original, "alpha")
    _write(healed, "beta")

    ctx = _mk_report_context([original])
    report = DiffFilesReport(base_dir)
    returned = report._generate_report(ctx)
    assert returned is ctx
