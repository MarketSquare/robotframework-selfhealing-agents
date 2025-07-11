from pydantic import BaseModel, Field


class PromptPayload(BaseModel):
    """Standard payload for healing operations.

    Attributes:
        robot_code_line: Formatted Robot Keyword object to string.
        error_msg: Robotframework error message.
        dom_tree: DOM tree of website on test failure.
    """

    robot_code_line: str = Field(
        ..., description="The raw Robot keyword call that failed"
    )
    error_msg: str = Field(..., description="The Robotframework error message")
    dom_tree: str = Field(..., description="DOM tree of website on test failure")
    keyword_name: str = Field(
        ..., description="Name of the Robotframework keyword that failed"
    )
    keyword_args: tuple = Field(
        ..., description="Arguments of the Robotframework keyword that failed"
    )
    failed_locator: str = Field(
        ..., description="Locator that failed in the Robotframework keyword"
    )
    tried_locator_memory: list = Field(
        ..., description="List of tried locator suggestions that still failed."
    )


class LocatorHealingResponse(BaseModel):
    """Response schema for locator healing response of locator agent.

    Attributes:
        suggestions: Contains suggestions for fixing locator error.
    """

    suggestions: list = Field(..., description="Suggestions for fixing locator error.")
