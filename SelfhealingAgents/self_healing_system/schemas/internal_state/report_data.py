from pydantic import BaseModel, ConfigDict, Field


class ReportData(BaseModel):
    """Data container for report generation in the self-healing system.

    Attributes:
        file (str): Name of the file where the error occurred.
        keyword_source (str): Absolute path of the keyword source file.
        test_name (str): Name of the test case.
        keyword (str): Failed keyword call.
        keyword_args (list): Arguments of the failed keyword call.
        lineno (int): Line number of the failed keyword call.
        failed_locator (str): Original failed locator.
        healed_locator (Optional[str]): Healed locator, if available.
        tried_locators (list): List of tried but failed locators.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    file: str = Field(..., description="Name of the file where the error occurred.")
    keyword_source: str = Field(..., description="Absolute path of the keyword source file.")
    test_name: str = Field(..., description="Name of the test case.")
    keyword: str = Field(..., description="Failed Keyword Call.")
    keyword_args: list = Field(..., description="Failed Keyword Arguments.")
    lineno: int = Field(..., description="Line number of failed keyword call.")
    failed_locator: str = Field(..., description="Original failed Locator.")
    healed_locator: str | None = Field(..., description="Healed locator.")
    tried_locators: list = Field(..., description="List of tried but failed locators.")
