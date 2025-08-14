import html
from typing import List
from pathlib import Path
from itertools import groupby
from operator import attrgetter

from RobotAid.self_healing_system.schemas.internal_state.report_context import ReportContext
from RobotAid.self_healing_system.reports.css_styles import ACTION_LOG_CSS
from RobotAid.self_healing_system.reports.report_types.base_report import BaseReport


class ActionLogReport(BaseReport):

    def __init__(self, base_dir: Path) -> None:
        super().__init__(base_dir, "action_log")

    def _generate_report(self, report_context: ReportContext) -> ReportContext:
        """Writes an HTML table summarizing each locator healing event.

        Args:
            report_info: List of data objects representing healing events.

        Raises:
            RuntimeError: If writing to the output file fails.
        """
        header: str = (
            "<html><head><meta charset='utf-8'><title>Locator Healing Report</title>"
            f"{ACTION_LOG_CSS}</head><body><h1>Locator Healing Report</h1>"
        )
        groups = sorted(report_context.report_info, key=attrgetter("file"))
        body_parts: List[str] = []
        for suite, entries in groupby(groups, key=attrgetter("file")):
            entries_list = list(entries)
            path = html.escape(entries_list[0].keyword_source)
            summary = (
                f"<details><summary>{html.escape(suite)}"
                f"<div class='path'>{path}</div></summary>"
            )
            inner_header = (
                "<table class='inner'>"
                "<tr><th>Test</th><th>Keyword</th><th>Keyword Args</th><th>Line Number</th>"
                "<th>Failed Locator</th><th>Healed Locator</th><th>Tried Locators</th></tr>"
            )
            rows: List[str] = []
            for e in entries_list:
                args = ", ".join(html.escape(str(a)) for a in e.keyword_args)
                tried = "<br>".join(html.escape(l) for l in e.tried_locators)
                rows.append(
                    "<tr>"
                    f"<td>{html.escape(e.test_name)}</td>"
                    f"<td>{html.escape(e.keyword)}</td>"
                    f"<td>{args}</td>"
                    f"<td>{html.escape(str(e.lineno))}</td>"
                    f"<td>{html.escape(e.failed_locator)}</td>"
                    f"<td>{html.escape(e.healed_locator or '')}</td>"
                    f"<td>{tried}</td>"
                    "</tr>"
                )
            inner_footer = "</table></details>"
            body_parts.append(summary + inner_header + "".join(rows) + inner_footer)
        footer: str = "</body></html>"
        content = header + "".join(body_parts) + footer
        output_path: Path = self.out_dir / "action_log.html"
        try:
            output_path.write_text(content, encoding="utf-8")
        except OSError as e:
            raise RuntimeError(f"Failed to write action log to {output_path}") from e

        return report_context