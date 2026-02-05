"""Healing agents for the self-healing system.

This module provides the agent registry and default agent registrations
for the extensible healing type architecture (ADR-001g).
"""
from SelfhealingAgents.self_healing_system.agents.healing_agent_registry import (
    HealingAgentRegistry,
    register_default_agents,
    AgentFactory,
)

__all__ = [
    "HealingAgentRegistry",
    "register_default_agents",
    "AgentFactory",
]
