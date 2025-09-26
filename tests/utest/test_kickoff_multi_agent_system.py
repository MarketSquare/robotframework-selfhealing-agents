import pytest
import asyncio
from typing import Any
from unittest.mock import MagicMock, AsyncMock
from types import SimpleNamespace

from SelfhealingAgents.self_healing_system.kickoff_multi_agent_system import KickoffMultiAgentSystem
from pydantic_ai import UnexpectedModelBehavior
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
    def fake_dom_factory(at: str) -> MagicMock:
        dom_mock: MagicMock = MagicMock(name=f"FakeDomUtility[{at}]")
        dom_mock.get_library_type.return_value = at
        return dom_mock

    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.context_retrieving.dom_utility_factory.DomUtilityFactory.create_dom_utility",
        lambda at: fake_dom_factory(at),
        raising=True,
    )
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.context_retrieving.robot_ctx_retriever.RobotCtxRetriever.get_context_payload",
        lambda result, dom_utility: MagicMock(name="FakePromptPayload"),
        raising=True,
    )
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.agents.locator_agent.locator_agent_factory.LocatorAgentFactory.create_agent",
        staticmethod(lambda at, cfg, dom_utility: MagicMock(name=f"FakeLocatorAgent[{at}]")),
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
    def fake_dom_utility(agent_type: str) -> MagicMock:
        dom_mock: MagicMock = MagicMock()
        dom_mock.get_library_type.return_value = agent_type
        return dom_mock
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.context_retrieving.dom_utility_factory.DomUtilityFactory.create_dom_utility",
        lambda agent_type: fake_dom_utility(agent_type),
        raising=True,
    )
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.context_retrieving.robot_ctx_retriever.RobotCtxRetriever.get_context_payload",
        fake_get_context_payload,
        raising=True,
    )
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.agents.locator_agent.locator_agent_factory.LocatorAgentFactory.create_agent",
        staticmethod(lambda agent_type, cfg, dom_utility: MagicMock()),
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


def test_kickoff_healing_falls_back_to_dom(monkeypatch: pytest.MonkeyPatch, fake_result: MagicMock, fake_cfg: MagicMock, fake_tried_locators: list[str]) -> None:
    fake_result.owner = "AppiumLibrary"

    def fake_dom_utility(agent_type: str) -> MagicMock:
        dom_mock: MagicMock = MagicMock(name=f"FakeDomUtility[{agent_type}]")
        dom_mock.get_library_type.return_value = agent_type
        dom_mock.get_locator_proposals.return_value = ["//fallback"]
        return dom_mock

    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.context_retrieving.dom_utility_factory.DomUtilityFactory.create_dom_utility",
        lambda agent_type: fake_dom_utility(agent_type),
        raising=True,
    )

    payload = SimpleNamespace(
        keyword_name="Click Element",
        failed_locator="//bad",
        tried_locator_memory=[],
    )

    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.context_retrieving.robot_ctx_retriever.RobotCtxRetriever.get_context_payload",
        lambda result, dom_utility: payload,
        raising=True,
    )

    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.agents.locator_agent.locator_agent_factory.LocatorAgentFactory.create_agent",
        lambda agent_type, cfg, dom_utility: MagicMock(),
        raising=True,
    )

    class FailingOrchestrator:
        def __init__(self, cfg, locator_agent) -> None:
            pass

        async def run_async(self, ctx) -> str:
            raise UnexpectedModelBehavior("invalid output")

    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.kickoff_multi_agent_system.OrchestratorAgent",
        FailingOrchestrator,
        raising=True,
    )

    monkeypatch.setattr(
        "asyncio.get_event_loop",
        lambda: SimpleNamespace(run_until_complete=lambda coro: asyncio.run(coro)),
        raising=True,
    )

    response = KickoffMultiAgentSystem.kickoff_healing(
        fake_result, cfg=fake_cfg, tried_locator_memory=fake_tried_locators
    )

    assert isinstance(response, LocatorHealingResponse)
    assert response.suggestions == ["//fallback"]



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
    def fake_dom(agent_type: str) -> MagicMock:
        dom_mock: MagicMock = MagicMock()
        dom_mock.get_library_type.return_value = agent_type
        return dom_mock
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.context_retrieving.dom_utility_factory.DomUtilityFactory.create_dom_utility",
        lambda agent_type: fake_dom(agent_type),
        raising=True,
    )
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.context_retrieving.robot_ctx_retriever.RobotCtxRetriever.get_context_payload",
        lambda result, dom_utility: MagicMock(),
        raising=True,
    )
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.agents.locator_agent.locator_agent_factory.LocatorAgentFactory.create_agent",
        staticmethod(lambda agent_type, cfg, dom_utility: MagicMock()),
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
