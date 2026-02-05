"""Unit tests for OrchestratorAgent with Programmatic Hand-Off.

Tests for ADR-001d orchestrator refactoring.
"""
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from SelfhealingAgents.self_healing_system.schemas.api.locator_healing import (
    LocatorHealingResponse,
    NoHealingNeededResponse,
)
from SelfhealingAgents.self_healing_system.schemas.internal_state.prompt_payload import (
    PromptPayload,
)


def _run(coro):
    """Helper to run async coroutines in tests."""
    return asyncio.run(coro)


class TestOrchestratorAgent:
    """Tests for OrchestratorAgent."""

    @pytest.fixture
    def mock_cfg(self):
        """Create mock configuration."""
        cfg = MagicMock()
        cfg.request_limit = 5
        cfg.total_tokens_limit = 6000
        return cfg

    @pytest.fixture
    def mock_locator_agent(self):
        """Create mock locator agent."""
        agent = MagicMock()
        agent.is_failed_locator_error = MagicMock(return_value=True)
        agent.heal_async = AsyncMock(return_value=LocatorHealingResponse(
            suggestions=["#new-btn", ".btn-primary"]
        ))
        return agent

    @pytest.fixture
    def mock_payload(self):
        """Create mock prompt payload."""
        return MagicMock(spec=PromptPayload, error_msg="Element not found")

    def test_orchestrator_routes_locator_error_to_agent(
        self, mock_cfg, mock_locator_agent, mock_payload
    ):
        """Orchestrator routes locator errors to locator agent."""
        from SelfhealingAgents.self_healing_system.agents.orchestrator_agent.orchestrator_agent import (
            OrchestratorAgent,
        )

        orchestrator = OrchestratorAgent(mock_cfg, mock_locator_agent)
        result = _run(orchestrator.run_async(mock_payload))

        # Should call heal_async on locator agent
        mock_locator_agent.heal_async.assert_called_once()
        assert isinstance(result, LocatorHealingResponse)

    def test_orchestrator_returns_no_healing_for_non_locator_error(
        self, mock_cfg, mock_locator_agent, mock_payload
    ):
        """Orchestrator returns NoHealingNeeded for non-locator errors."""
        from SelfhealingAgents.self_healing_system.agents.orchestrator_agent.orchestrator_agent import (
            OrchestratorAgent,
        )

        # Configure agent to reject this error
        mock_locator_agent.is_failed_locator_error.return_value = False
        mock_payload.error_msg = "Some non-locator error"

        orchestrator = OrchestratorAgent(mock_cfg, mock_locator_agent)
        result = _run(orchestrator.run_async(mock_payload))

        # Should NOT call heal_async
        mock_locator_agent.heal_async.assert_not_called()
        assert isinstance(result, NoHealingNeededResponse)

    def test_orchestrator_passes_usage_to_locator_agent(
        self, mock_cfg, mock_locator_agent, mock_payload
    ):
        """Orchestrator passes RunUsage to locator agent for tracking."""
        from SelfhealingAgents.self_healing_system.agents.orchestrator_agent.orchestrator_agent import (
            OrchestratorAgent,
        )

        orchestrator = OrchestratorAgent(mock_cfg, mock_locator_agent)
        _run(orchestrator.run_async(mock_payload))

        # Check that heal_async was called with usage parameter
        call_kwargs = mock_locator_agent.heal_async.call_args.kwargs
        assert "usage" in call_kwargs
        assert "usage_limits" in call_kwargs

    def test_orchestrator_no_llm_agent_created(self, mock_cfg, mock_locator_agent):
        """Orchestrator does not create an LLM agent (Programmatic Hand-Off)."""
        from SelfhealingAgents.self_healing_system.agents.orchestrator_agent.orchestrator_agent import (
            OrchestratorAgent,
        )

        orchestrator = OrchestratorAgent(mock_cfg, mock_locator_agent)

        # Should not have _agent attribute (no LLM agent)
        assert not hasattr(orchestrator, "_agent")

    def test_orchestrator_has_usage_limits(self, mock_cfg, mock_locator_agent):
        """Orchestrator initializes usage limits from config."""
        from SelfhealingAgents.self_healing_system.agents.orchestrator_agent.orchestrator_agent import (
            OrchestratorAgent,
        )

        orchestrator = OrchestratorAgent(mock_cfg, mock_locator_agent)

        assert orchestrator._usage_limits.request_limit == 5
        assert orchestrator._usage_limits.total_tokens_limit == 6000
