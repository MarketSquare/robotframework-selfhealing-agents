import html
from typing import List
from pathlib import Path
from itertools import groupby
from operator import attrgetter

from RobotAid.utils.logging import log
from RobotAid.self_healing_system.reports.css_styles import ACTION_LOG_CSS
from RobotAid.self_healing_system.reports.report_types.base_report import BaseReport
from RobotAid.self_healing_system.schemas.internal_state.report_data import ReportData
from RobotAid.self_healing_system.schemas.internal_state.report_context import ReportContext


class ActionLogReport(BaseReport):
    """Generates an HTML action log summarizing locator healing events.

    This report creates an HTML table that groups and displays all locator healing
    events, including test names, keywords, arguments, line numbers, failed and healed
    locators, and all tried locators. The report is saved in the reports directory.
    """
    def __init__(self, base_dir: Path) -> None:
        """Initializes the ActionLogReport with the given base directory.

        Args:
            base_dir: The base directory where the action log will be saved.
        """
        super().__init__(base_dir, "action_log")

    @log
    def _generate_report(self, report_context: ReportContext) -> ReportContext:
        """Writes an HTML table summarizing each locator healing event.

        Groups healing events by file and generates a detailed HTML report
        with all relevant information for each event.

        Args:
            report_context: The context object containing healing event data.

        Returns:
            The updated ReportContext after generating the action log.

        Raises:
            RuntimeError: If writing to the output file fails.
        """
        header: str = (
            "<html><head><meta charset='utf-8'><title>Locator Healing Report</title>"
            f"{ACTION_LOG_CSS}</head><body><h1>Locator Healing Report</h1>"
        )
        groups: List[ReportData] = sorted(report_context.report_info, key=attrgetter("file"))
        body_parts: List[str] = []
        for suite, entries in groupby(groups, key=attrgetter("file")):
            entries_list: List[ReportData] = list(entries)
            path: str = html.escape(entries_list[0].keyword_source)
            summary: str = (
                f"<details><summary>{html.escape(suite)}"
                f"<div class='path'>{path}</div></summary>"
            )
            inner_header: str = (
                "<table class='inner'>"
                "<tr><th>Test</th><th>Keyword</th><th>Keyword Args</th><th>Line Number</th>"
                "<th>Failed Locator</th><th>Healed Locator</th><th>Tried Locators</th></tr>"
            )
            rows: List[str] = []
            for e in entries_list:
                args: str = ", ".join(html.escape(str(a)) for a in e.keyword_args)
                tried: str = "<br>".join(html.escape(l) for l in e.tried_locators)
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
            inner_footer: str = "</table></details>"
            body_parts.append(summary + inner_header + "".join(rows) + inner_footer)
        footer: str = "</body></html>"
        content: str = header + "".join(body_parts) + footer
        output_path: Path = self._out_dir / "action_log.html"
        try:
            output_path.write_text(content, encoding="utf-8")
        except OSError as e:
            raise RuntimeError(f"Failed to write action log to {output_path}") from e

        return report_context