from typing import List
from pathlib import Path

from pydantic import BaseModel, Field

from RobotAid.self_healing_system.schemas.internal_state.report_data import ReportData


class ReportContext(BaseModel):

    report_info: List[ReportData] = Field(..., description="Report info containing data about healed locators.")
    external_resource_paths: List[Path] = Field(default_factory=list, description="Paths of external resource files.")