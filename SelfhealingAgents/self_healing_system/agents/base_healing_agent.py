"""Base healing agent abstract class.

Part of ADR-001g - Extensible Healing Type Architecture.
Defines the contract for all healing agent implementations.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic_ai.usage import RunUsage, UsageLimits

from SelfhealingAgents.self_healing_system.error_classification.healing_types import HealingType

if TYPE_CHECKING:
    from SelfhealingAgents.self_healing_system.schemas.internal_state.healing_payload import HealingPayload
    from SelfhealingAgents.utils.cfg import Cfg


class BaseHealingAgent(ABC):
    """Abstract base class for all healing agents.

    Each healing type (locator, timing, assertion, mandatory_field) should
    have a concrete implementation that inherits from this class.

    The agent contract requires:
    - heal_async(): Perform the healing operation
    - classify_error(): Check if this agent can handle an error
    - gather_context(): Collect type-specific context for healing
    - supported_healing_types: Class attribute listing supported types
    """

    # Class attribute: healing types this agent supports
    supported_healing_types: tuple[HealingType, ...] = ()

    def __init__(self, cfg: "Cfg") -> None:
        """Initialize the healing agent.

        Args:
            cfg: Application configuration.
        """
        self._cfg = cfg

    @abstractmethod
    async def heal_async(
        self,
        payload: "HealingPayload",
        *,
        usage: RunUsage | None = None,
        usage_limits: UsageLimits | None = None,
    ) -> "HealingResponse":
        """Perform healing for the given payload.

        Args:
            payload: The healing payload with error context.
            usage: Shared usage tracker for token counting.
            usage_limits: Token/request limits for this run.

        Returns:
            Healing response appropriate to the healing type.
        """
        pass

    @classmethod
    @abstractmethod
    def classify_error(cls, error_message: str) -> bool:
        """Check if this agent can handle the given error.

        This is used for routing in the orchestrator when multiple
        healing types might apply.

        Args:
            error_message: The error message to classify.

        Returns:
            True if this agent can handle the error.
        """
        pass

    @abstractmethod
    async def gather_context(
        self, payload: "HealingPayload"
    ) -> "HealingPayload":
        """Gather type-specific context for healing.

        Enriches the payload with additional context needed for
        this healing type (DOM tree for locators, screenshots for
        assertions, etc.).

        Args:
            payload: The initial healing payload.

        Returns:
            Enriched payload with type-specific context.
        """
        pass


# Type alias for healing responses (will be union of all response types)
HealingResponse = object  # Placeholder - will be union type
