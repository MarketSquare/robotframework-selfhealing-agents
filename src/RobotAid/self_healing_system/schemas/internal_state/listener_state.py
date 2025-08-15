from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field

from RobotAid.utils.cfg import Cfg
from RobotAid.self_healing_system.schemas.internal_state.report_data import ReportData


class ListenerState(BaseModel):
    """Schema for maintaining listener state in the self-healing system.

    Attributes:
        cfg (Cfg): Configuration object for the self-healing system.
        context (Dict[str, Any]): Dictionary for storing contextual information during execution.
        report_info (List[ReportData]): List of ReportData objects representing healing events.
        retry_count (int): Number of retries attempted by the self-healing system.
        suggestions (Optional[List[str]]): List of locator suggestions for healing.
        should_generate_locators (bool): Indicates if locator suggestions should be generated.
        tried_locators (List[str]): List of locators that have been tried.
        healed (bool): Indicates if the current locator has been healed.
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