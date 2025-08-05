from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from RobotAid.utils.cfg import Cfg
from RobotAid.self_healing_system.schemas.internal_state.report_data import ReportData


class ListenerState(BaseModel):
    """Schema for listener state handling.

    Attributes:
        TODO
    """

    cfg: Cfg = Field(..., description="Configuration pydantic class.")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context dictionary.")
    report_info: List[ReportData] = Field(
        default_factory=list,
        description="List of ReportData objects."
    )
    retry_count: int = Field(0, gt=0, description="Retry count of self-healing system.")
    suggestions: Optional[List[str]] = Field(None, description="Locators suggestions.")
    should_generate_locators: bool = Field(
        True, description="True if current locators suggestions should be generated."
    )
    tried_locators: List[str] = Field(default_factory=list)
    healed: bool = Field(False, description="True if current locator is healed.")