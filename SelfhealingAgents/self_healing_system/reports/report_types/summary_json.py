import json
from pathlib import Path

from SelfhealingAgents.utils.logging import log
from SelfhealingAgents.self_healing_system.reports.report_types.base_report import BaseReport
from SelfhealingAgents.self_healing_system.schemas.internal_state.report_context import ReportContext


class SummaryJson(BaseReport):
    """Generates a summary JSON report of self-healing events.

    This report aggregates statistics about healing events, affected tests, and files,
    and saves the summary as a JSON file in the output directory.
    """
    def __init__(self, base_dir: Path) -> None:
        """Initializes the SummaryJson report with the given base directory.

        Args:
            base_dir: The base directory where the summary report will be saved.
        """
        super().__init__(base_dir, "summary")

    @log
    def _generate_report(self, report_context: ReportContext) -> ReportContext:
        """Generates and saves a summary of healing events as a JSON file.

        Aggregates the total number of healing events, the number of affected tests and files,
        and lists their names. The summary is written to 'summary.json' in the output directory.

        Args:
            report_context: The context object containing healing event data.

        Returns:
            The unchanged ReportContext object.

        Raises:
            OSError: If writing the summary JSON file fails.
        """
        summary = {
            "total_healing_events": len(report_context.report_info),
            "nr_affected_tests": len(list({r.test_name for r in report_context.report_info})),
            "nr_affected_files": len(list({r.file for r in report_context.report_info})),
            "affected_tests": list({r.test_name for r in report_context.report_info}),
            "affected_files": list({r.file for r in report_context.report_info}),
        }

        summary_path = self._out_dir / "summary.json"
        with summary_path.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        return report_context
