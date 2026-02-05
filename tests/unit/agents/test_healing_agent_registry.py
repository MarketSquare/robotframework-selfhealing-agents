"""Unit tests for HealingAgentRegistry.

Tests for ADR-001g healing agent registry.
"""
import pytest
from unittest.mock import MagicMock

from SelfhealingAgents.self_healing_system.error_classification.healing_types import HealingType


class TestHealingAgentRegistry:
    """Tests for HealingAgentRegistry."""

    @pytest.fixture(autouse=True)
    def clear_registry(self):
        """Clear registry before each test."""
        from SelfhealingAgents.self_healing_system.agents.healing_agent_registry import (
            HealingAgentRegistry,
        )
        registry = HealingAgentRegistry()
        registry.clear()
        yield
        registry.clear()

    def test_registry_is_singleton(self):
        """Registry uses singleton pattern."""
        from SelfhealingAgents.self_healing_system.agents.healing_agent_registry import (
            HealingAgentRegistry,
        )

        reg1 = HealingAgentRegistry()
        reg2 = HealingAgentRegistry()

        assert reg1 is reg2

    def test_register_and_get_agent(self):
        """Can register and retrieve agent factory."""
        from SelfhealingAgents.self_healing_system.agents.healing_agent_registry import (
            HealingAgentRegistry,
        )

        registry = HealingAgentRegistry()

        mock_agent = MagicMock()
        mock_factory = MagicMock(return_value=mock_agent)

        registry.register(HealingType.LOCATOR, "selenium", mock_factory)

        cfg = MagicMock()
        agent = registry.get_agent(HealingType.LOCATOR, "selenium", cfg)

        mock_factory.assert_called_once_with(cfg)
        assert agent is mock_agent

    def test_wildcard_fallback(self):
        """Wildcard '*' acts as fallback."""
        from SelfhealingAgents.self_healing_system.agents.healing_agent_registry import (
            HealingAgentRegistry,
        )

        registry = HealingAgentRegistry()

        mock_agent = MagicMock()
        mock_factory = MagicMock(return_value=mock_agent)

        # Register only wildcard
        registry.register(HealingType.TIMING, "*", mock_factory)

        cfg = MagicMock()

        # Should match via wildcard
        agent = registry.get_agent(HealingType.TIMING, "selenium", cfg)
        assert agent is mock_agent

        # Should also match other libraries
        agent2 = registry.get_agent(HealingType.TIMING, "browser", cfg)
        assert agent2 is mock_agent

    def test_exact_match_preferred_over_wildcard(self):
        """Exact library match is preferred over wildcard."""
        from SelfhealingAgents.self_healing_system.agents.healing_agent_registry import (
            HealingAgentRegistry,
        )

        registry = HealingAgentRegistry()

        exact_agent = MagicMock()
        wildcard_agent = MagicMock()
        exact_factory = MagicMock(return_value=exact_agent)
        wildcard_factory = MagicMock(return_value=wildcard_agent)

        registry.register(HealingType.LOCATOR, "selenium", exact_factory)
        registry.register(HealingType.LOCATOR, "*", wildcard_factory)

        cfg = MagicMock()

        # selenium should get exact match
        agent = registry.get_agent(HealingType.LOCATOR, "selenium", cfg)
        assert agent is exact_agent

        # browser should get wildcard
        agent2 = registry.get_agent(HealingType.LOCATOR, "browser", cfg)
        assert agent2 is wildcard_agent

    def test_raises_key_error_when_not_found(self):
        """Raises KeyError when no agent registered."""
        from SelfhealingAgents.self_healing_system.agents.healing_agent_registry import (
            HealingAgentRegistry,
        )

        registry = HealingAgentRegistry()
        cfg = MagicMock()

        with pytest.raises(KeyError) as exc_info:
            registry.get_agent(HealingType.ASSERTION, "selenium", cfg)

        assert "No healing agent registered" in str(exc_info.value)

    def test_has_agent_returns_true_for_registered(self):
        """has_agent returns True for registered combinations."""
        from SelfhealingAgents.self_healing_system.agents.healing_agent_registry import (
            HealingAgentRegistry,
        )

        registry = HealingAgentRegistry()
        registry.register(HealingType.LOCATOR, "selenium", MagicMock())

        assert registry.has_agent(HealingType.LOCATOR, "selenium") is True
        assert registry.has_agent(HealingType.LOCATOR, "browser") is False

    def test_has_agent_considers_wildcard(self):
        """has_agent considers wildcard fallback."""
        from SelfhealingAgents.self_healing_system.agents.healing_agent_registry import (
            HealingAgentRegistry,
        )

        registry = HealingAgentRegistry()
        registry.register(HealingType.TIMING, "*", MagicMock())

        assert registry.has_agent(HealingType.TIMING, "selenium") is True
        assert registry.has_agent(HealingType.TIMING, "browser") is True
        assert registry.has_agent(HealingType.LOCATOR, "selenium") is False

    def test_list_registered(self):
        """list_registered returns all registered keys."""
        from SelfhealingAgents.self_healing_system.agents.healing_agent_registry import (
            HealingAgentRegistry,
        )

        registry = HealingAgentRegistry()
        registry.register(HealingType.LOCATOR, "selenium", MagicMock())
        registry.register(HealingType.LOCATOR, "browser", MagicMock())
        registry.register(HealingType.TIMING, "*", MagicMock())

        registered = registry.list_registered()

        assert (HealingType.LOCATOR, "selenium") in registered
        assert (HealingType.LOCATOR, "browser") in registered
        assert (HealingType.TIMING, "*") in registered
        assert len(registered) == 3

    def test_clear_removes_all_registrations(self):
        """clear removes all registered factories."""
        from SelfhealingAgents.self_healing_system.agents.healing_agent_registry import (
            HealingAgentRegistry,
        )

        registry = HealingAgentRegistry()
        registry.register(HealingType.LOCATOR, "selenium", MagicMock())
        registry.register(HealingType.TIMING, "*", MagicMock())

        registry.clear()

        assert len(registry.list_registered()) == 0
