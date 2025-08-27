from pydantic import BaseModel, Field


class PromptPayload(BaseModel):
    """Standard payload for healing operations in the self-healing system.

    Attributes:
        robot_code_line (str): The raw Robot Framework keyword call that failed.
        error_msg (str): The Robot Framework error message.
        dom_tree (str): DOM tree of the website at the time of test failure.
        keyword_name (str): Name of the Robot Framework keyword that failed.
        keyword_args (tuple): Arguments of the Robot Framework keyword that failed.
        failed_locator (str): Locator that failed in the Robot Framework keyword.
        tried_locator_memory (list): List of tried locator suggestions that still failed.
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