"""Healing payload model for multi-healing-type support.

Part of ADR-001g - Extensible Healing Type Architecture.
Flat model with optional type-specific fields (Design Decision D1).
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field as PydanticField

from SelfhealingAgents.self_healing_system.error_classification.healing_types import HealingType


class HealingPayload(BaseModel):
    """Unified payload for all healing types.

    Uses a flat model design (ADR D1) with optional type-specific fields.
    Core fields are required; type-specific fields are optional.

    Core Fields (always required):
        error_msg: The error message from the test failure.
        keyword_name: The Robot Framework keyword that failed.
        keyword_args: Arguments passed to the failed keyword.
        robot_code_line: The line of Robot code that failed.

    Locator-Specific Fields:
        dom_tree: HTML DOM context around the failed element.
        failed_locator: The locator string that failed.
        page_source: Full page HTML source.
        tried_locator_memory: Previously attempted locators.

    Timing-Specific Fields:
        timeout_value: The timeout that was exceeded.
        expected_condition: The condition being waited for.
        actual_wait_time: How long the wait actually ran.

    Assertion-Specific Fields:
        expected_value: The expected assertion value.
        actual_value: The actual value received.
        assertion_type: Type of assertion (equals, contains, etc.).

    Mandatory Field-Specific Fields:
        field_name: Name of the missing required field.
        form_context: Form HTML context.

    Context Enrichment Fields:
        screenshot_path: Path to failure screenshot.
        user_story: Related user story text.
        test_case_context: Full test case context.

    Classification Fields:
        healing_type_hint: Pre-classified healing type if known.
    """

    # --- Core fields (required) ---
    error_msg: str = PydanticField(..., description="The error message from the test failure")
    keyword_name: str = PydanticField(..., description="The Robot Framework keyword that failed")
    keyword_args: tuple = PydanticField(..., description="Arguments passed to the failed keyword")
    robot_code_line: str = PydanticField(..., description="The line of Robot code that failed")

    # --- Locator-specific fields ---
    dom_tree: str | None = PydanticField(None, description="HTML DOM context around the failed element")
    failed_locator: str | None = PydanticField(None, description="The locator string that failed")
    page_source: str | None = PydanticField(None, description="Full page HTML source")
    tried_locator_memory: list[str] = PydanticField(default_factory=list, description="Previously attempted locators")
    locator_type: str | None = PydanticField(None, description="Type of locator (css, xpath, etc.)")

    # --- Timing-specific fields ---
    timeout_value: float | None = PydanticField(None, description="The timeout that was exceeded (seconds)")
    expected_condition: str | None = PydanticField(None, description="The condition being waited for")
    actual_wait_time: float | None = PydanticField(None, description="How long the wait actually ran (seconds)")

    # --- Assertion-specific fields ---
    expected_value: Any | None = PydanticField(None, description="The expected assertion value")
    actual_value: Any | None = PydanticField(None, description="The actual value received")
    assertion_type: str | None = PydanticField(None, description="Type of assertion (equals, contains, etc.)")

    # --- Mandatory field-specific fields ---
    field_name: str | None = PydanticField(None, description="Name of the missing required field")
    form_context: str | None = PydanticField(None, description="Form HTML context")

    # --- Context enrichment fields ---
    screenshot_path: str | None = PydanticField(None, description="Path to failure screenshot")
    user_story: str | None = PydanticField(None, description="Related user story text")
    test_case_context: str | None = PydanticField(None, description="Full test case context")

    # --- Classification fields ---
    healing_type_hint: HealingType | None = PydanticField(None, description="Pre-classified healing type if known")

    # --- Backward compatibility with PromptPayload ---
    # These mirror PromptPayload fields for gradual migration
    action_performed: str | None = PydanticField(None, description="Action that was performed")
    library_imports: str | None = PydanticField(None, description="Library imports in the test")

    model_config = {"extra": "allow"}  # Allow additional fields for extensibility
