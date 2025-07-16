from pydantic import BaseModel, ConfigDict, Field


class ReportData(BaseModel):
    """Data container for report generation.

    Attributes:
        file (str): Name of the file where the error occurred.
        keyword_source (str): Absolute path of the keyword source file.
        test_name (str): Name of the test name.
        keyword (str): Failed Keyword Call.
        keyword_args (list): Failed Keyword Arguments.
        healed_locator (str): Healed Locator.
        tried_locators (list): List of tried but failed locators.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    file: str = Field(..., description="Name of the file where the error occurred.")
    keyword_source: str = Field(..., description="Absolute path of the keyword source file.")
    test_name: str = Field(..., description="Name of the test case.")
    keyword: str = Field(..., description="Failed Keyword Call.")
    keyword_args: list = Field(..., description="Failed Keyword Arguments.")
    healed_locator: str | None = Field(..., description="Healed locator.")
    tried_locators: list = Field(..., description="List of tried but failed locators.")
