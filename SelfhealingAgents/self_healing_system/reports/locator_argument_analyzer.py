from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple

_VAR_PATTERN = re.compile(r"\$\{[^}]+\}")


@dataclass(frozen=True)
class ArgumentAnalysisResult:
    token_value: str
    variable_updates: List[Tuple[str, str]]


def analyze_locator_argument(
    raw_argument: str | None,
    failed_locator: str,
    healed_locator: str,
) -> ArgumentAnalysisResult:
    """Derives how a keyword argument should change to reflect a healed locator.

    The analyzer focuses on arguments composed of exactly one Robot Framework
    variable followed by an optional literal suffix, which reflects how most
    Browser keywords build selectors (e.g. ``${MAIN_SELECTOR} img``).

    If the structure cannot be determined confidently, the function falls back
    to replacing the entire argument with the healed locator and skips variable
    updates. This guarantees that healed files diverge from the originals while
    keeping the logic conservative for unknown patterns.
    """

    if not raw_argument:
        return ArgumentAnalysisResult(token_value=healed_locator, variable_updates=[])

    match = _VAR_PATTERN.search(raw_argument)
    if not match:
        # No variable placeholder present – treat the whole argument as literal.
        return ArgumentAnalysisResult(token_value=healed_locator, variable_updates=[])

    var_token = match.group()
    prefix = raw_argument[: match.start()]
    suffix = raw_argument[match.end() :]

    if prefix and not healed_locator.startswith(prefix):
        # Unexpected prefix mutation – fall back to literal replacement.
        return ArgumentAnalysisResult(token_value=healed_locator, variable_updates=[])

    # Compute the portion of the locator that belongs to the variable in the
    # failing run by cutting the known prefix/suffix pieces away.
    remaining_failed = failed_locator[len(prefix) :] if prefix else failed_locator
    if suffix:
        if not remaining_failed.endswith(suffix):
            return ArgumentAnalysisResult(token_value=healed_locator, variable_updates=[])
        original_var_value = remaining_failed[: -len(suffix)]
    else:
        original_var_value = remaining_failed

    remaining_healed = healed_locator[len(prefix) :] if prefix else healed_locator
    new_suffix = suffix
    new_var_value = original_var_value

    if suffix and remaining_healed.endswith(suffix):
        # Case 1: literal suffix stayed the same -> only variables changed.
        new_var_value = remaining_healed[: -len(suffix)]
    elif remaining_healed.startswith(original_var_value):
        # Case 2: variable part untouched, literal suffix changed.
        new_suffix = remaining_healed[len(original_var_value) :]
    else:
        # Case 3: both parts changed – approximate the split using the
        # original variable length to keep the structure predictable.
        split_index = len(original_var_value)
        if split_index <= 0 or split_index > len(remaining_healed):
            split_index = len(remaining_healed)
        new_var_value = remaining_healed[:split_index]
        new_suffix = remaining_healed[split_index:]

    token_value = f"{prefix}{var_token}{new_suffix}"
    variable_updates: List[Tuple[str, str]] = []
    if new_var_value != original_var_value:
        variable_updates.append((var_token, new_var_value))

    return ArgumentAnalysisResult(token_value=token_value, variable_updates=variable_updates)
