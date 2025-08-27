from pathlib import Path
from abc import ABC, abstractmethod

from SelfhealingAgents.self_healing_system.schemas.internal_state.report_context import ReportContext


class BaseReport(ABC):
    """Abstract base class for report generation in the self-healing system.

    Subclasses must implement the _generate_report method to define how specific
    report types are generated. Handles output directory setup and provides a
    common interface for generating reports.

    Attributes:
        _base_dir (Path): The base directory where reports are stored.
        _out_dir (Path): The output directory for this specific report type.
    """
    def __init__(self, base_dir: Path, subfolder: str) -> None:
        """Initializes the BaseReport with base and output directories.

        Args:
            base_dir: The base directory where reports are stored.
            subfolder: The subfolder name for this specific report type.
        """
        self._base_dir: Path = base_dir
        self._out_dir: Path = base_dir / subfolder

    def generate_report(self, ctx: ReportContext) -> ReportContext:
        """Ensures the output directory exists and generates the report.

        Args:
            ctx: The ReportContext object containing data needed for report generation.

        Returns:
            The updated ReportContext after report generation.
        """
        self._out_dir.mkdir(parents=True, exist_ok=True)
        return self._generate_report(ctx)

    @abstractmethod
    def _generate_report(self, report_context: ReportContext) -> ReportContext:
        """Abstract method for generating a report.

        Subclasses must implement this method to define the report generation logic.

        Args:
            report_context: The ReportContext object containing data needed for report generation.

        Returns:
            The updated ReportContext after report generation.
        """
        pass