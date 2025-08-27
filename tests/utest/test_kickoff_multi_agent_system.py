import pytest
import asyncio
from typing import Any
from unittest.mock import MagicMock, AsyncMock

from SelfhealingAgents.self_healing_system.kickoff_multi_agent_system import KickoffMultiAgentSystem
from SelfhealingAgents.self_healing_system.schemas.api.locator_healing import (
    LocatorHealingResponse,
    NoHealingNeededResponse
)


@pytest.fixture
def fake_result() -> MagicMock:
    obj: MagicMock = MagicMock()
    obj.owner = "SeleniumLibrary"
    return obj


@pytest.fixture
def fake_cfg() -> MagicMock:
    return MagicMock()


@pytest.fixture
def fake_tried_locators() -> list[str]:
    return ["foo", "bar"]


def patch_factories_and_ctx(
    monkeypatch: pytest.MonkeyPatch,
    *,
    agent_type: str = "selenium",
    orchestrator_response: Any = LocatorHealingResponse(suggestions=["healing-response"]),
) -> MagicMock:
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.context_retrieving.dom_utility_factory.DomUtilityFactory.create_dom_utility",
        lambda at: MagicMock(name=f"FakeDomUtility[{at}]"),
        raising=True,
    )
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.context_retrieving.robot_ctx_retriever.RobotCtxRetriever.get_context_payload",
        lambda result, dom_utility: MagicMock(name="FakePromptPayload"),
        raising=True,
    )
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.agents.locator_agent.locator_agent_factory.LocatorAgentFactory.create_agent",
        lambda at, cfg, dom_utility: MagicMock(name=f"FakeLocatorAgent[{at}]"),
        raising=True,
    )
    mocked_orchestrator: MagicMock = MagicMock(name="FakeOrchestratorAgent")
    mocked_orchestrator.run_async = AsyncMock(return_value=orchestrator_response)
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.kickoff_multi_agent_system.OrchestratorAgent",
        lambda cfg, locator_agent: mocked_orchestrator,
        raising=True,
    )
    monkeypatch.setattr(
        "asyncio.get_event_loop",
        lambda: MagicMock(run_until_complete=lambda coro: asyncio.run(coro)),
        raising=True,
    )
    return mocked_orchestrator


def test_kickoff_healing_happy_path(
    monkeypatch: pytest.MonkeyPatch,
    fake_result: MagicMock,
    fake_cfg: MagicMock,
    fake_tried_locators: list[str],
) -> None:
    patch_factories_and_ctx(
        monkeypatch,
        agent_type="selenium",
        orchestrator_response=LocatorHealingResponse(suggestions=["healing-response"]),
    )
    fake_result.owner = "SeleniumLibrary"
    result: LocatorHealingResponse | str | NoHealingNeededResponse = KickoffMultiAgentSystem.kickoff_healing(
        fake_result, cfg=fake_cfg, tried_locator_memory=fake_tried_locators
    )
    assert result == LocatorHealingResponse(suggestions=["healing-response"])


@pytest.mark.parametrize(
    "lib,agent_type",
    [
        ("SeleniumLibrary", "selenium"),
        ("Browser", "browser"),
        ("AppiumLibrary", "appium"),
    ],
)
def test_kickoff_healing_library_mapping(
    monkeypatch: pytest.MonkeyPatch,
    fake_result: MagicMock,
    fake_cfg: MagicMock,
    fake_tried_locators: list[str],
    lib: str,
    agent_type: str,
) -> None:
    patch_factories_and_ctx(monkeypatch, agent_type=agent_type, orchestrator_response="ok")
    fake_result.owner = lib
    result: LocatorHealingResponse | str | NoHealingNeededResponse = KickoffMultiAgentSystem.kickoff_healing(
        fake_result, cfg=fake_cfg, tried_locator_memory=fake_tried_locators
    )
    assert result == "ok"


def test_kickoff_healing_unsupported_library(
    fake_result: MagicMock,
    fake_cfg: MagicMock,
    fake_tried_locators: list[str],
) -> None:
    fake_result.owner = "UnknownLibrary"
    with pytest.raises(ValueError):
        KickoffMultiAgentSystem.kickoff_healing(
            fake_result, cfg=fake_cfg, tried_locator_memory=fake_tried_locators
        )


def test_kickoff_healing_context_payload_and_tried_locators(
    monkeypatch: pytest.MonkeyPatch,
    fake_result: MagicMock,
    fake_cfg: MagicMock,
    fake_tried_locators: list[str],
) -> None:
    context_payload: MagicMock = MagicMock()
    def fake_get_context_payload(result: MagicMock, dom_utility: MagicMock) -> MagicMock:
        return context_payload
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.context_retrieving.dom_utility_factory.DomUtilityFactory.create_dom_utility",
        lambda agent_type: MagicMock(),
        raising=True,
    )
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.context_retrieving.robot_ctx_retriever.RobotCtxRetriever.get_context_payload",
        fake_get_context_payload,
        raising=True,
    )
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.agents.locator_agent.locator_agent_factory.LocatorAgentFactory.create_agent",
        lambda agent_type, cfg, dom_utility: MagicMock(),
        raising=True,
    )
    fake_orchestrator: MagicMock = MagicMock()
    fake_orchestrator.run_async = AsyncMock(return_value="resp")
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.kickoff_multi_agent_system.OrchestratorAgent",
        lambda cfg, locator_agent: fake_orchestrator,
        raising=True,
    )
    monkeypatch.setattr(
        "asyncio.get_event_loop",
        lambda: MagicMock(run_until_complete=lambda coro: asyncio.run(coro)),
        raising=True,
    )
    fake_result.owner = "SeleniumLibrary"
    _ = KickoffMultiAgentSystem.kickoff_healing(
        fake_result, cfg=fake_cfg, tried_locator_memory=fake_tried_locators
    )
    assert context_payload.tried_locator_memory == fake_tried_locators


def test_kickoff_healing_asyncio_run_until_complete(
    monkeypatch: pytest.MonkeyPatch,
    fake_result: MagicMock,
    fake_cfg: MagicMock,
    fake_tried_locators: list[str],
) -> None:
    patch_factories_and_ctx(monkeypatch, agent_type="selenium", orchestrator_response="async-result")
    fake_result.owner = "SeleniumLibrary"
    result: LocatorHealingResponse | str | NoHealingNeededResponse = KickoffMultiAgentSystem.kickoff_healing(
        fake_result, cfg=fake_cfg, tried_locator_memory=fake_tried_locators
    )
    assert result == "async-result"


def test_kickoff_healing_orchestrator_exception(
    monkeypatch: pytest.MonkeyPatch,
    fake_result: MagicMock,
    fake_cfg: MagicMock,
    fake_tried_locators: list[str],
) -> None:
    def raise_exc(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("orchestrator failed")
    fake_orchestrator: MagicMock = MagicMock()
    fake_orchestrator.run_async = AsyncMock(side_effect=raise_exc)
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.context_retrieving.dom_utility_factory.DomUtilityFactory.create_dom_utility",
        lambda agent_type: MagicMock(),
        raising=True,
    )
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.context_retrieving.robot_ctx_retriever.RobotCtxRetriever.get_context_payload",
        lambda result, dom_utility: MagicMock(),
        raising=True,
    )
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.agents.locator_agent.locator_agent_factory.LocatorAgentFactory.create_agent",
        lambda agent_type, cfg, dom_utility: MagicMock(),
        raising=True,
    )
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.kickoff_multi_agent_system.OrchestratorAgent",
        lambda cfg, locator_agent: fake_orchestrator,
        raising=True,
    )
    monkeypatch.setattr(
        "asyncio.get_event_loop",
        lambda: MagicMock(run_until_complete=lambda coro: asyncio.run(coro)),
        raising=True,
    )
    fake_result.owner = "SeleniumLibrary"
    with pytest.raises(RuntimeError, match="orchestrator failed"):
        _ = KickoffMultiAgentSystem.kickoff_healing(
            fake_result, cfg=fake_cfg, tried_locator_memory=fake_tried_locators
        )
