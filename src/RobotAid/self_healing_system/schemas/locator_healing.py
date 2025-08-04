from pydantic import BaseModel, Field


class LocatorHealingResponse(BaseModel):
    """Response schema for locator healing response of locator agent.

    Attributes:
        suggestions: Contains suggestions for fixing locator error.
        metadata: Contains metadata about each locator suggestion
    """

    suggestions: list = Field(..., description="Suggestions for fixing locator error.")
    metadata: list = Field(
        default=[], description="Metadata about each locator suggestion."
    )


class NoHealingNeededResponse(BaseModel):
    """Response schema for cases where no healing is needed.

    Attributes:
        message: Message indicating no healing is needed.
    """

    message: str = Field(..., description="Message indicating no healing is needed.")
