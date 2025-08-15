from typing import List
from pathlib import Path

from pydantic import BaseModel, Field

from RobotAid.self_healing_system.schemas.internal_state.report_data import ReportData


class ReportContext(BaseModel):
    """Context object for report generation in the self-healing system.

    Attributes:
        report_info (List[ReportData]): List containing data about healed locators and healing events.
        external_resource_paths (List[Path]): Paths to external resource files referenced in the report.
    """
    report_info: List[ReportData] = Field(..., description="Report info containing data about healed locators.")
    external_resource_paths: List[Path] = Field(default_factory=list, description="Paths of external resource files.")