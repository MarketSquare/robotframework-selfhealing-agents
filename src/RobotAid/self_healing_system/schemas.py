from typing import List
from pydantic import BaseModel, Field


# Schemas are implemented but act as examples for now, will be adjusted to context.
class PromptPayload(BaseModel):
    """Standard payload for healing operations.

    Attributes:
        robot_code_line (str): Formatted Robot Keyword object to string.
        error_msg (str): Robotframework error message.
        dom_tree (str): DOM tree of website on test failure.
    """
    robot_code_line: str = Field(..., description="The raw Robot keyword call that failed")
    error_msg: str = Field(..., description="The Robotframework error message")
    dom_tree: str = Field(..., description="DOM tree of website on test failure")


class LocatorHealingResponse(BaseModel):
    """Final healing output: a list of fixed locators.

    Attributes:
        suggestions (List): Suggestions for fixed locators.
    """
    suggestions: List[str] = Field(..., description='List of repaired locators suggestions')