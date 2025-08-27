import shutil
from typing import List
from pathlib import Path

from SelfhealingAgents.utils.logging import log
from SelfhealingAgents.self_healing_system.reports.report_types.base_report import BaseReport
from SelfhealingAgents.self_healing_system.schemas.internal_state.report_data import ReportData
from SelfhealingAgents.self_healing_system.schemas.internal_state.report_context import ReportContext
from SelfhealingAgents.self_healing_system.reports.report_types.action_log_report import ActionLogReport
from SelfhealingAgents.self_healing_system.reports.report_types.healed_files_report import HealedFilesReport
from SelfhealingAgents.self_healing_system.reports.report_types.diff_files_report import DiffFilesReport


class ReportGenerator:
    """Generates reports for self-healing events in Robot Framework test suites.

    This class creates action logs, healed Robot Framework test suites or resources,
    and diff files that document the changes made during self-healing. It uses the
    "Chain-of-Responsibility" and "Context Object" design patterns to process and
    generate multiple report types in sequence.

    Attributes:
        _base_dir (Path): The base directory where all reports are generated.
        _report_types (List[BaseReport]): List of report type handlers used to generate different reports.
    """

    def __init__(self, base_dir: Path = None) -> None:
        """Initializes the ReportGenerator and sets up the report directories.

        The reports directory is created under the project workspace. If it already
        exists, it is removed and recreated to ensure a clean state for each run.

        Args:
            base_dir (Path): The base directory where all reports are generated for unit testing.
        """
        self._base_dir: Path = base_dir or (Path.cwd() / "SelfhealingReports" / "reports")
        if self._base_dir.exists():
            shutil.rmtree(self._base_dir)
        self._base_dir.mkdir(parents=True)

        self._report_types: List[BaseReport] = [
            ActionLogReport(self._base_dir),
            HealedFilesReport(self._base_dir),
            DiffFilesReport(self._base_dir)
        ]

    @log
    def generate_reports(self, report_info: List[ReportData]) -> None:
        """Generates all report types for the provided healing event data.

        This method processes the given list of healing events and generates
        action logs, healed .robot and .resource files, and diff files.

        Args:
            report_info: A list of ReportData objects representing healing events.
        """
        ctx: ReportContext = ReportContext(report_info=report_info)
        for rt in self._report_types:
            ctx: ReportContext = rt.generate_report(ctx)