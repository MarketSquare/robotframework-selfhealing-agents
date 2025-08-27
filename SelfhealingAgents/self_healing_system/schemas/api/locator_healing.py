from pydantic import BaseModel, Field


class LocatorHealingResponse(BaseModel):
    """Response schema for locator healing results from the locator agent.

    Attributes:
        suggestions (list): Suggestions for fixing the locator error.
        metadata (list): Metadata about each locator suggestion.
    """
    suggestions: list = Field(..., description="Suggestions for fixing locator error.")
    metadata: list = Field(
        default=[], description="Metadata about each locator suggestion."
    )


class NoHealingNeededResponse(BaseModel):
    """Response schema for cases where no locator healing is needed.

    Attributes:
        message (str): Message indicating that no healing is required.
    """
    message: str = Field(..., description="Message indicating no healing is needed.")
