"""Error classifier with tiered classification strategy.

Part of ADR-001g - Extensible Healing Type Architecture.

Tier 1: Deterministic regex-based pattern matching (fast, no LLM).
Tier 2: LLM-based classification for ambiguous cases (future).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from pydantic import BaseModel, Field as PydanticField

from .healing_types import HealingType


class ErrorClassification(BaseModel):
    """Result of error classification.

    Attributes:
        healing_type: The primary healing type identified.
        confidence: Classification confidence (0.0-1.0). Tier 1 always 1.0.
        tier: Classification tier used (1=regex, 2=LLM).
        alternatives: Other possible healing types for ambiguous cases.
        reasoning: Explanation of classification decision.
        raw_error: The original error message.
    """
    healing_type: HealingType = PydanticField(...)
    confidence: float = PydanticField(default=1.0, ge=0.0, le=1.0)
    tier: int = PydanticField(..., ge=1, le=2)
    alternatives: list[HealingType] = PydanticField(default_factory=list)
    reasoning: str = PydanticField(default="")
    raw_error: str = PydanticField(...)


@dataclass
class PatternEntry:
    """A compiled regex pattern for error classification."""
    pattern: re.Pattern
    healing_type: HealingType
    description: str = ""


class PatternRegistry:
    """Registry of error patterns for tier-1 classification.

    Thread-safe singleton that maintains compiled regex patterns
    for fast error classification without LLM calls.
    """
    _instance: PatternRegistry | None = None
    _patterns: list[PatternEntry] = field(default_factory=list)

    def __new__(cls) -> PatternRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._patterns = []
            cls._instance._register_default_patterns()
        return cls._instance

    def _register_default_patterns(self) -> None:
        """Register built-in patterns for common error types."""
        # Locator errors
        self.register(
            r"element.*not found|no.*element.*matches|could not.*locate|"
            r"unable to locate|element.*does not exist|"
            r"stale element|element is not attached|"
            r"nosuchelement|elementnotfound|"
            r"waiting.*element.*failed|"
            r"locator.*did not match|selector.*not found",
            HealingType.LOCATOR,
            "Element locator failure patterns"
        )

        # Timing errors
        self.register(
            r"timeout|timed out|wait.*exceeded|"
            r"page load.*timeout|script.*timeout|"
            r"async.*timeout|promise.*timeout|"
            r"deadline exceeded|operation.*took too long",
            HealingType.TIMING,
            "Timeout and timing failure patterns"
        )

        # Assertion errors
        self.register(
            r"assertion.*failed|assert.*error|"
            r"expected.*but.*got|should.*equal|"
            r"should.*be|should.*contain|"
            r"does not match expected|"
            r"comparison failed|value mismatch",
            HealingType.ASSERTION,
            "Assertion failure patterns"
        )

        # Mandatory field errors
        self.register(
            r"required.*field|mandatory.*missing|"
            r"field.*is required|missing required|"
            r"cannot be null|cannot be empty|"
            r"validation.*failed.*required",
            HealingType.MANDATORY_FIELD,
            "Missing required field patterns"
        )

    def register(
        self,
        pattern: str,
        healing_type: HealingType,
        description: str = "",
    ) -> None:
        """Register a new pattern for classification.

        Args:
            pattern: Regex pattern (case-insensitive).
            healing_type: The healing type this pattern indicates.
            description: Human-readable description.
        """
        compiled = re.compile(pattern, re.IGNORECASE)
        self._patterns.append(PatternEntry(compiled, healing_type, description))

    def classify(self, error_message: str) -> ErrorClassification | None:
        """Classify an error message using registered patterns.

        Args:
            error_message: The error message to classify.

        Returns:
            ErrorClassification if a pattern matches, None otherwise.
        """
        for entry in self._patterns:
            if entry.pattern.search(error_message):
                return ErrorClassification(
                    healing_type=entry.healing_type,
                    confidence=1.0,
                    tier=1,
                    reasoning=f"Matched pattern: {entry.description}",
                    raw_error=error_message,
                )
        return None


def classify_error(error_message: str) -> ErrorClassification:
    """Classify an error message into a healing type.

    Uses tiered classification:
    1. Tier 1: Fast regex-based pattern matching
    2. Tier 2: LLM-based classification (future, for ambiguous cases)

    Args:
        error_message: The error message to classify.

    Returns:
        ErrorClassification with the detected healing type.
    """
    registry = PatternRegistry()

    # Tier 1: Pattern matching
    result = registry.classify(error_message)
    if result is not None:
        return result

    # Tier 2: Would use LLM here for ambiguous cases
    # For now, return UNKNOWN
    return ErrorClassification(
        healing_type=HealingType.UNKNOWN,
        confidence=0.5,
        tier=1,
        reasoning="No pattern matched; classified as UNKNOWN",
        raw_error=error_message,
    )
