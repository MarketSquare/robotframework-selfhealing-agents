from pydantic import BaseModel, ConfigDict, Field


class ReportData(BaseModel):
    """Data container for report generation.

    Attributes:
        test_suite (str): Name of the test suite.
        suite_abs_path (str): Absolute path of the test suite.
        test_name (str): Name of the test name.
        keyword (str): Failed Keyword Call.
        keyword_args (list): Failed Keyword Arguments.
        healed_locator (str): Healed Locator.
        tried_locators (list): List of tried but failed locators.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    test_suite: str = Field(..., description="Name of the test suite.")
    suite_abs_path: str = Field(..., description="Absolute path of the test suite.")
    test_name: str = Field(..., description="Name of the test case.")
    keyword: str = Field(..., description="Failed Keyword Call.")
    keyword_args: list = Field(..., description="Failed Keyword Arguments.")
    healed_locator: str | None = Field(..., description="Healed locator.")
    tried_locators: list = Field(..., description="List of tried but failed locators.")
