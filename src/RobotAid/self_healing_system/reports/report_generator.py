import shutil
from typing import List
from pathlib import Path

from RobotAid.self_healing_system.reports.report_types.base_report import BaseReport
from RobotAid.self_healing_system.schemas.internal_state.report_data import ReportData
from RobotAid.self_healing_system.schemas.internal_state.report_context import ReportContext
from RobotAid.self_healing_system.reports.report_types.action_log_report import ActionLogReport
from RobotAid.self_healing_system.reports.report_types.healed_files_report import HealedFilesReport
from RobotAid.self_healing_system.reports.report_types.diff_files_report import DiffFilesReport


class ReportGenerator:
    """Generates action log, healed Robot Framework test suites (and/or resources) and diff files with the respective
       changes.

       Uses "Chain-of-Responsibility + Context Object" pattern
    """

    def __init__(self) -> None:
        """Initialize report directories under the project workspace."""
        workspace_dir: Path = Path(__file__).resolve().parents[4]
        self._base_dir: Path = workspace_dir / "reports"
        if self._base_dir.exists():
            shutil.rmtree(self._base_dir)
        self._base_dir.mkdir(parents=True)

        self._report_types: List[BaseReport] = [
            ActionLogReport(self._base_dir),
            HealedFilesReport(self._base_dir),
            DiffFilesReport(self._base_dir)
        ]

    def generate_reports(self, report_info: List[ReportData]) -> None:
        """Generate action log, healed .robot and .resource files, and diff files for given report data.

        Args:
            report_info: List of data objects representing healing events.
        """
        ctx: ReportContext = ReportContext(report_info=report_info)
        for rt in self._report_types:
            ctx: ReportContext = rt.generate_report(ctx)