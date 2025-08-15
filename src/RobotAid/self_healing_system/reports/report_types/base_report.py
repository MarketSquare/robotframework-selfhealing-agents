from pathlib import Path
from abc import ABC, abstractmethod

from RobotAid.self_healing_system.schemas.internal_state.report_context import ReportContext


class BaseReport(ABC):

    def __init__(self, base_dir: Path, subfolder: str) -> None:
        self.base_dir: Path = base_dir
        self.out_dir: Path = base_dir / subfolder

    def generate_report(self, ctx: ReportContext) -> ReportContext:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        return self._generate_report(ctx)

    @abstractmethod
    def _generate_report(self, report_context: ReportContext) -> ReportContext:
        pass