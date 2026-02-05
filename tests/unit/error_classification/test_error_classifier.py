"""Unit tests for error classification module.

Tests for ADR-001g error classifier.
"""
import pytest

from SelfhealingAgents.self_healing_system.error_classification.healing_types import HealingType
from SelfhealingAgents.self_healing_system.error_classification.error_classifier import (
    ErrorClassification,
    PatternRegistry,
    classify_error,
)


class TestHealingType:
    """Tests for HealingType enum."""

    def test_healing_type_values(self):
        """All expected healing types exist."""
        assert HealingType.LOCATOR.value == "locator"
        assert HealingType.TIMING.value == "timing"
        assert HealingType.ASSERTION.value == "assertion"
        assert HealingType.MANDATORY_FIELD.value == "mandatory_field"
        assert HealingType.UNKNOWN.value == "unknown"

    def test_healing_type_is_string_enum(self):
        """HealingType values are strings."""
        assert isinstance(HealingType.LOCATOR, str)
        assert HealingType.LOCATOR == "locator"


class TestErrorClassification:
    """Tests for ErrorClassification model."""

    def test_error_classification_creation(self):
        """ErrorClassification can be created with required fields."""
        result = ErrorClassification(
            healing_type=HealingType.LOCATOR,
            tier=1,
            raw_error="Element not found",
        )
        assert result.healing_type == HealingType.LOCATOR
        assert result.tier == 1
        assert result.confidence == 1.0  # default
        assert result.alternatives == []  # default

    def test_error_classification_with_alternatives(self):
        """ErrorClassification can include alternatives."""
        result = ErrorClassification(
            healing_type=HealingType.LOCATOR,
            tier=1,
            raw_error="Timeout waiting for element",
            alternatives=[HealingType.TIMING],
        )
        assert HealingType.TIMING in result.alternatives


class TestPatternRegistry:
    """Tests for PatternRegistry."""

    def test_registry_is_singleton(self):
        """PatternRegistry uses singleton pattern."""
        reg1 = PatternRegistry()
        reg2 = PatternRegistry()
        assert reg1 is reg2

    def test_default_patterns_registered(self):
        """Default patterns are registered on creation."""
        registry = PatternRegistry()
        # Should be able to classify a known locator error
        result = registry.classify("Element with locator 'css:#btn' not found.")
        assert result is not None
        assert result.healing_type == HealingType.LOCATOR

    def test_classify_locator_error(self):
        """Locator errors are correctly classified."""
        registry = PatternRegistry()

        test_cases = [
            "Element with locator 'css:#submit-btn' not found.",
            "Could not locate element with id 'login'.",
            "Unable to locate element: #missing",
            "StaleElementException: element is not attached to DOM",
            "NoSuchElementException: no such element",
        ]

        for error_msg in test_cases:
            result = registry.classify(error_msg)
            assert result is not None, f"Failed to classify: {error_msg}"
            assert result.healing_type == HealingType.LOCATOR, f"Wrong type for: {error_msg}"

    def test_classify_timing_error(self):
        """Timing errors are correctly classified."""
        registry = PatternRegistry()

        test_cases = [
            "TimeoutException: timed out after 10 seconds",
            "Timeout waiting for element to be visible",
            "page load timeout exceeded",
            "Operation timed out",
        ]

        for error_msg in test_cases:
            result = registry.classify(error_msg)
            assert result is not None, f"Failed to classify: {error_msg}"
            assert result.healing_type == HealingType.TIMING, f"Wrong type for: {error_msg}"

    def test_classify_assertion_error(self):
        """Assertion errors are correctly classified."""
        registry = PatternRegistry()

        test_cases = [
            "AssertionError: assertion failed",
            "Expected 'OK' but got 'Error'",
            "Value should be 'active' but was 'inactive'",
            "Element should contain 'success' but did not",
        ]

        for error_msg in test_cases:
            result = registry.classify(error_msg)
            assert result is not None, f"Failed to classify: {error_msg}"
            assert result.healing_type == HealingType.ASSERTION, f"Wrong type for: {error_msg}"

    def test_classify_mandatory_field_error(self):
        """Mandatory field errors are correctly classified."""
        registry = PatternRegistry()

        test_cases = [
            "ValidationError: required field 'email' is missing",
            "Field is required and cannot be null",
            "Error: mandatory field is missing from form",
        ]

        for error_msg in test_cases:
            result = registry.classify(error_msg)
            assert result is not None, f"Failed to classify: {error_msg}"
            assert result.healing_type == HealingType.MANDATORY_FIELD, f"Wrong type for: {error_msg}"

    def test_classify_unknown_returns_none(self):
        """Unknown errors return None from PatternRegistry."""
        registry = PatternRegistry()

        result = registry.classify("Some random error message with no patterns")
        assert result is None

    def test_custom_pattern_registration(self):
        """Custom patterns can be registered."""
        registry = PatternRegistry()

        # Register a custom pattern
        registry.register(
            r"custom error pattern",
            HealingType.TIMING,
            "Test custom pattern"
        )

        result = registry.classify("This is a custom error pattern message")
        assert result is not None
        assert result.healing_type == HealingType.TIMING


class TestClassifyError:
    """Tests for classify_error() function."""

    def test_classify_error_returns_classification(self):
        """classify_error always returns an ErrorClassification."""
        result = classify_error("Element not found")

        assert isinstance(result, ErrorClassification)
        assert result.healing_type == HealingType.LOCATOR

    def test_classify_error_unknown_fallback(self):
        """Unknown errors are classified as UNKNOWN."""
        result = classify_error("Completely random unmatched error xyz123")

        assert result.healing_type == HealingType.UNKNOWN
        assert result.tier == 1
        assert result.confidence < 1.0  # Lower confidence for unknown

    def test_classify_error_includes_raw_error(self):
        """Classification includes the original error message."""
        error_msg = "Element with locator '#btn' not found."
        result = classify_error(error_msg)

        assert result.raw_error == error_msg
