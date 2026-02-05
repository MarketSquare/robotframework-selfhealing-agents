"""Error classification module for healing type detection.

New module. Part of ADR-001g.
"""
from .healing_types import HealingType
from .error_classifier import ErrorClassification, PatternRegistry, classify_error

__all__ = ["HealingType", "ErrorClassification", "PatternRegistry", "classify_error"]
