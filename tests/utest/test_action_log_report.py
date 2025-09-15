import pytest
from typing import List
from pathlib import Path

import SelfhealingAgents.self_healing_system.reports.report_types.action_log_report as action_module
from SelfhealingAgents.self_healing_system.schemas.internal_state.report_data import ReportData
from SelfhealingAgents.self_healing_system.schemas.internal_state.report_context import ReportContext
from SelfhealingAgents.self_healing_system.reports.report_types.action_log_report import ActionLogReport


def _mk_report_data(
    *,
    file: str,
    keyword_source: str,
    test_name: str = "Test Case",
    locator_origin: str = "Test Case",
    keyword: str = "KW",
    keyword_args: List[object] | None = None,
    lineno: int = 1,
    failed_locator: str = "orig",
    healed_locator: str | None = "healed",
    tried_locators: List[str] | None = None,
) -> ReportData:
    return ReportData(
        file=file,
        keyword_source=keyword_source,
        test_name=test_name,
        locator_origin=locator_origin,
        keyword=keyword,
        keyword_args=[] if keyword_args is None else keyword_args,
        lineno=lineno,
        failed_locator=failed_locator,
        healed_locator=healed_locator,
        tried_locators=[] if tried_locators is None else tried_locators,
    )


def _ensure_outdir(report: ActionLogReport) -> Path:
    out_dir = getattr(report, "_out_dir")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def test_writes_action_log_file_and_injects_css(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base_dir = tmp_path
    monkeypatch.setattr(action_module, "ACTION_LOG_CSS", "<style>.action-css{}</style>", raising=True)

    d1 = _mk_report_data(
        file="suite1.robot",
        keyword_source=str(base_dir / "suites" / "suite1.robot"),
        test_name="T1",
        locator_origin="T1",
        keyword="Click",
        keyword_args=["#btn", 42],
        lineno=10,
        failed_locator="id=old",
        healed_locator="id=new",
        tried_locators=["id=old", "css=.btn"],
    )
    ctx = ReportContext(report_info=[d1], external_resource_paths=[])

    report = ActionLogReport(base_dir)
    out_dir = _ensure_outdir(report)

    ret = report._generate_report(ctx)
    assert ret is ctx

    out_path = out_dir / "action_log.html"
    assert out_path.exists()

    html = out_path.read_text(encoding="utf-8")
    assert "<style>.action-css{}</style>" in html
    assert "<h1>Locator Healing Report</h1>" in html
    assert "suite1.robot" in html
    assert "T1" in html
    assert "Click" in html
    assert "#btn, 42" in html
    assert ">10<" in html
    assert "id=old" in html
    assert "id=new" in html
    assert "id=old<br>css=.btn" in html


def test_groups_by_file_and_sorts_stably(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base_dir = tmp_path
    monkeypatch.setattr(action_module, "ACTION_LOG_CSS", "", raising=True)

    a1 = _mk_report_data(file="a.robot", keyword_source="/x/a.robot", test_name="A1", lineno=1)
    a2 = _mk_report_data(file="a.robot", keyword_source="/x/a.robot", test_name="A2", lineno=2)
    b1 = _mk_report_data(file="b.robot", keyword_source="/y/b.robot", test_name="B1", lineno=3)

    ctx = ReportContext(report_info=[b1, a2, a1], external_resource_paths=[])
    report = ActionLogReport(base_dir)
    out_dir = _ensure_outdir(report)

    report._generate_report(ctx)

    out_html = (out_dir / "action_log.html").read_text(encoding="utf-8")

    first_group_idx = out_html.index("<details><summary>a.robot")
    second_group_idx = out_html.index("<details><summary>b.robot")
    assert first_group_idx < second_group_idx

    assert out_html.count("<details><summary>a.robot") == 1
    assert out_html.count("<details><summary>b.robot") == 1
    assert "A1" in out_html and "A2" in out_html and "B1" in out_html


def test_html_escaping_in_all_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base_dir = tmp_path
    monkeypatch.setattr(action_module, "ACTION_LOG_CSS", "", raising=True)

    d = _mk_report_data(
        file="suite<&>.robot",
        keyword_source="/weird/<&>.robot",
        test_name="Case<&>",
        keyword="Click<&>",
        keyword_args=["arg<&>", {"k": "v<&>"}],
        lineno=7,
        failed_locator="css=a<b>",
        healed_locator="xpath=//a[@id='x&y']",
        tried_locators=["one<&>", "two<&>"],
    )

    ctx = ReportContext(report_info=[d], external_resource_paths=[])
    report = ActionLogReport(base_dir)
    out_dir = _ensure_outdir(report)

    report._generate_report(ctx)
    html = (out_dir / "action_log.html").read_text(encoding="utf-8")

    assert "suite&lt;&amp;&gt;.robot" in html
    assert "<div class='path'>/weird/&lt;&amp;&gt;.robot</div>" in html
    assert "Case&lt;&amp;&gt;" in html
    assert "Click&lt;&amp;&gt;" in html
    assert "arg&lt;&amp;&gt;" in html
    assert "{&#x27;k&#x27;: &#x27;v&lt;&amp;&gt;&#x27;}" in html
    assert "7" in html
    assert "css=a&lt;b&gt;" in html
    assert "xpath=//a[@id=&#x27;x&amp;y&#x27;]" in html
    assert "one&lt;&amp;&gt;<br>two&lt;&amp;&gt;" in html


def test_empty_report_info_still_writes_valid_html(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base_dir = tmp_path
    monkeypatch.setattr(action_module, "ACTION_LOG_CSS", "", raising=True)

    ctx = ReportContext(report_info=[], external_resource_paths=[])
    report = ActionLogReport(base_dir)
    out_dir = _ensure_outdir(report)

    report._generate_report(ctx)

    out_path = out_dir / "action_log.html"
    html = out_path.read_text(encoding="utf-8")
    assert html.startswith("<html>")
    assert html.endswith("</html>")
    assert "<details><summary>" not in html


def test_multiple_rows_structure_and_headers_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base_dir = tmp_path
    monkeypatch.setattr(action_module, "ACTION_LOG_CSS", "", raising=True)

    d1 = _mk_report_data(file="s.robot", keyword_source="/p/s.robot", test_name="T1", keyword="K1", lineno=1)
    d2 = _mk_report_data(file="s.robot", keyword_source="/p/s.robot", test_name="T2", keyword="K2", lineno=2)
    ctx = ReportContext(report_info=[d1, d2], external_resource_paths=[])

    report = ActionLogReport(base_dir)
    out_dir = _ensure_outdir(report)

    report._generate_report(ctx)

    html = (out_dir / "action_log.html").read_text(encoding="utf-8")
    assert "<table class='inner'>" in html
    assert "<th>Test</th>" in html
    assert "<th>Keyword</th>" in html
    assert "<th>Keyword Args</th>" in html
    assert "<th>Line Number</th>" in html
    assert "<th>Failed Locator</th>" in html
    assert "<th>Healed Locator</th>" in html
    assert "<th>Tried Locators</th>" in html
    assert html.count("<tr>") >= 3


def test_raises_runtime_error_on_write_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base_dir = tmp_path
    d = _mk_report_data(file="s.robot", keyword_source="/p/s.robot")
    ctx = ReportContext(report_info=[d], external_resource_paths=[])
    report = ActionLogReport(base_dir)
    out_dir = _ensure_outdir(report)

    bad_path = out_dir / "action_log.html"
    orig_write_text = Path.write_text

    def fake_write_text(self: Path, data: str, encoding: str = "utf-8") -> int:
        if self == bad_path:
            raise OSError("simulated write error")
        return orig_write_text(self, data, encoding=encoding)

    monkeypatch.setattr(Path, "write_text", fake_write_text, raising=True)

    with pytest.raises(RuntimeError) as ei:
        report._generate_report(ctx)

    assert "Failed to write action log to" in str(ei.value)
    assert str(bad_path) in str(ei.value)
