"""Healing agent registry for factory-based agent resolution.

Part of ADR-001g - Extensible Healing Type Architecture.
Uses factory pattern with flat tuple keys and wildcard support (Design Decision D2).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from SelfhealingAgents.self_healing_system.error_classification.healing_types import HealingType

if TYPE_CHECKING:
    from SelfhealingAgents.self_healing_system.agents.locator_agent.base_locator_agent import BaseLocatorAgent
    from SelfhealingAgents.utils.cfg import Cfg


# Type alias for agent factory functions
AgentFactory = Callable[["Cfg"], "BaseLocatorAgent"]


class HealingAgentRegistry:
    """Registry for healing agent factories.

    Maps (HealingType, library_type) tuples to factory functions that
    create the appropriate healing agent. Supports wildcard '*' for
    library_type to provide fallback agents.

    Usage:
        registry = HealingAgentRegistry()
        registry.register(HealingType.LOCATOR, "selenium", SeleniumLocatorAgentFactory)
        registry.register(HealingType.LOCATOR, "*", GenericLocatorAgentFactory)

        agent = registry.get_agent(HealingType.LOCATOR, "selenium", cfg)
    """

    _instance: HealingAgentRegistry | None = None

    def __new__(cls) -> HealingAgentRegistry:
        """Singleton pattern for global registry access."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._factories: dict[tuple[HealingType, str], AgentFactory] = {}
        return cls._instance

    def register(
        self,
        healing_type: HealingType,
        library_type: str,
        factory: AgentFactory,
    ) -> None:
        """Register an agent factory for a healing type and library.

        Args:
            healing_type: The type of healing (LOCATOR, TIMING, etc.).
            library_type: The RF library ('selenium', 'browser', 'appium', or '*' for wildcard).
            factory: A callable that takes Cfg and returns a BaseLocatorAgent.
        """
        key = (healing_type, library_type)
        self._factories[key] = factory

    def get_agent(
        self,
        healing_type: HealingType,
        library_type: str,
        cfg: "Cfg",
    ) -> "BaseLocatorAgent":
        """Get or create an agent for the given healing type and library.

        Lookup order:
        1. Exact match: (healing_type, library_type)
        2. Wildcard fallback: (healing_type, '*')
        3. Raise KeyError if no match

        Args:
            healing_type: The type of healing needed.
            library_type: The RF library type.
            cfg: Application configuration.

        Returns:
            A configured healing agent instance.

        Raises:
            KeyError: If no factory is registered for this combination.
        """
        # Try exact match first
        key = (healing_type, library_type)
        if key in self._factories:
            return self._factories[key](cfg)

        # Try wildcard fallback
        wildcard_key = (healing_type, "*")
        if wildcard_key in self._factories:
            return self._factories[wildcard_key](cfg)

        raise KeyError(
            f"No healing agent registered for {healing_type.value}/{library_type}. "
            f"Registered: {list(self._factories.keys())}"
        )

    def has_agent(
        self,
        healing_type: HealingType,
        library_type: str,
    ) -> bool:
        """Check if an agent is available for this combination.

        Args:
            healing_type: The type of healing.
            library_type: The RF library type.

        Returns:
            True if an agent (exact or wildcard) is registered.
        """
        key = (healing_type, library_type)
        wildcard_key = (healing_type, "*")
        return key in self._factories or wildcard_key in self._factories

    def list_registered(self) -> list[tuple[HealingType, str]]:
        """List all registered (healing_type, library_type) combinations.

        Returns:
            List of registered keys.
        """
        return list(self._factories.keys())

    def clear(self) -> None:
        """Clear all registered factories. Useful for testing."""
        self._factories.clear()


def register_default_agents() -> None:
    """Register the default healing agents.

    Called during system initialization to populate the registry
    with built-in agents.
    """
    from SelfhealingAgents.self_healing_system.agents.locator_agent.selenium_locator_agent import (
        SeleniumLocatorAgent,
    )
    from SelfhealingAgents.self_healing_system.agents.locator_agent.browser_locator_agent import (
        BrowserLocatorAgent,
    )
    from SelfhealingAgents.self_healing_system.context_retrieving.dom_utility_factory import (
        DomUtilityFactory,
    )

    registry = HealingAgentRegistry()

    # Locator agents - library-specific
    def selenium_locator_factory(cfg):
        dom_utility = DomUtilityFactory.create_dom_utility("selenium")
        return SeleniumLocatorAgent(cfg, dom_utility)

    def browser_locator_factory(cfg):
        dom_utility = DomUtilityFactory.create_dom_utility("browser")
        return BrowserLocatorAgent(cfg, dom_utility)

    registry.register(HealingType.LOCATOR, "selenium", selenium_locator_factory)
    registry.register(HealingType.LOCATOR, "browser", browser_locator_factory)

    # Future: register timing, assertion, mandatory_field agents
    # registry.register(HealingType.TIMING, "*", timing_agent_factory)
    # registry.register(HealingType.ASSERTION, "*", assertion_agent_factory)
    # registry.register(HealingType.MANDATORY_FIELD, "*", mandatory_field_agent_factory)
