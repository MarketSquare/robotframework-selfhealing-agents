from typing import List
from pydantic import BaseModel, Field


# Schemas are implemented but act as examples for now, will be adjusted to context.
class PromptPayload(BaseModel):
    """Standard payload for healing operations.

    Attributes:
        failure_details (str): Test suite failure details.
    """
    failure_details: str = Field(...)

class LocatorSuggestionsResponse(BaseModel):
    """Response from locator generation agent.

    Attributes:
        suggestions (List): Suggestions for fixed locators.
    """
    suggestions: List[str] = Field(...)

class LocatorHealingResponse(BaseModel):
    """Final healing output: a list of fixed locators.

    Attributes:
        suggestions (List): Suggestions for fixed locators.
    """
    suggestions: List[str] = Field(..., description='List of repaired locators')