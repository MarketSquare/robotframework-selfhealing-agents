"""Healing type enumeration for error classification.

Part of ADR-001g - Extensible Healing Type Architecture.
"""
from enum import Enum


class HealingType(str, Enum):
    """Enumeration of supported healing types.

    Each healing type corresponds to a category of test failures
    that can be automatically remediated.

    Values:
        LOCATOR: Element locator failures (CSS, XPath, accessibility).
        TIMING: Timeout and wait-related failures.
        ASSERTION: Test assertion failures.
        MANDATORY_FIELD: Missing required field failures.
        UNKNOWN: Unclassified failures requiring manual review.
    """
    LOCATOR = "locator"
    TIMING = "timing"
    ASSERTION = "assertion"
    MANDATORY_FIELD = "mandatory_field"
    UNKNOWN = "unknown"
