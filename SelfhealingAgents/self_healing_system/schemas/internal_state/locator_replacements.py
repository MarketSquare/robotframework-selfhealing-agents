from pydantic import BaseModel, Field


class LocatorReplacements(BaseModel):
    """Schema for maintaining listener state in the self-healing system.

    Attributes:
        test_case (str): Name of the test case.
        locator_origin (str): Origin where the locator is called (Test or Keyword).
        failed_locator (str): Original failed locator.
        healed_locator (Optional[str]): Healed locator, if available.
    """
    test_case: str = Field(..., description="Test where the replacements will be done.")
    locator_origin: str = Field(..., description="Origin where the locator is called (Test or Keyword).")
    failed_locator: str = Field(..., description="Original locator that failed.")
    healed_locator: str = Field(..., description="Healed locator that replaces the failed one.")
    keyword_args: list[str] | None = Field(
        default=None,
        description="Raw keyword arguments at the time of failure to help reconstruct locators.",
    )