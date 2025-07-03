import asyncio
from typing import Any, cast

import pytest
from robot import result

from RobotAid.self_healing_system.kickoff_self_healing import \
    KickoffSelfHealing
from RobotAid.self_healing_system.schemas import LocatorHealingResponse
from RobotAid.utils.app_settings import AppSettings
from RobotAid.utils.client_settings import ClientSettings


class DummyKeyword:
    def __init__(self):
        self.owner = "Browser"


class DummyAppSettings:
    pass


class DummyClientSettings:
    pass


class DummyLocatorAgent:
    def __init__(self, app_settings: Any, client_settings: Any, usage_limits: Any = None, dom_utility: Any = None, agent_type: Any = None, **kwargs) -> None:
        self.app_settings = app_settings
        self.client_settings = client_settings
        self.usage_limits = usage_limits
        self.dom_utility = dom_utility
        self.agent_type = agent_type


class DummyOrchestratorAgent:
    def __init__(self, locator_agent: Any, app_settings: Any, client_settings: Any, usage_limits: Any = None, **kwargs) -> None:
        self.locator_agent = locator_agent
        self.app_settings = app_settings
        self.client_settings = client_settings
        self.usage_limits = usage_limits

    async def run_async(self, robot_ctx: dict) -> str:
        return "{\"suggestions\": [\"fix1\", \"fix2\", \"fix3\"]}"


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    monkeypatch.setattr(
        "RobotAid.self_healing_system.kickoff_self_healing.RobotCtxRetriever.get_context",
        lambda result, dom_utility: {"failed": True},
    )
    monkeypatch.setattr(
        "RobotAid.self_healing_system.kickoff_self_healing.DomUtilityFactory.create_dom_utility",
        lambda utility_type: None,
    )
    monkeypatch.setattr(
        "RobotAid.self_healing_system.kickoff_self_healing.LocatorAgent",
        lambda app_settings, client_settings, usage_limits=None, dom_utility=None, agent_type=None, **kwargs: DummyLocatorAgent(
            app_settings=app_settings,
            client_settings=client_settings,
            usage_limits=usage_limits,
            dom_utility=dom_utility,
            agent_type=agent_type,
        ),
    )
    monkeypatch.setattr(
        "RobotAid.self_healing_system.kickoff_self_healing.OrchestratorAgent",
        lambda locator_agent, app_settings, client_settings, usage_limits=None, **kwargs: DummyOrchestratorAgent(
            locator_agent=locator_agent,
            app_settings=app_settings,
            client_settings=client_settings,
            usage_limits=usage_limits,
        ),
    )
    monkeypatch.setattr(
        asyncio,
        "run",
        lambda coro: asyncio.new_event_loop().run_until_complete(coro),
    )


def test_kickoff_healing_happy_path() -> None:
    dummy_result = cast(result.Keyword, DummyKeyword())
    dummy_app = cast(AppSettings, DummyAppSettings())
    dummy_client = cast(ClientSettings, DummyClientSettings())

    response = KickoffSelfHealing.kickoff_healing(
        result=dummy_result,
        app_settings=dummy_app,
        client_settings=dummy_client,
        tried_locator_memory=list()
    )

    assert isinstance(response, LocatorHealingResponse)
    assert response == LocatorHealingResponse(suggestions=['fix1', 'fix2', 'fix3'])


def test_kickoff_healing_passes_context_and_settings() -> None:
    captured = {}

    class SpyOrchestrator(DummyOrchestratorAgent):
        def __init__(self, locator_agent, app_settings, client_settings, usage_limits=None) -> None:
            super().__init__(locator_agent=locator_agent,
                             app_settings=app_settings,
                             client_settings=client_settings,
                             usage_limits=usage_limits)
            captured['locator_agent'] = locator_agent
            captured['app_settings'] = app_settings
            captured['client_settings'] = client_settings

        async def run_async(self, robot_ctx):
            captured['robot_ctx'] = robot_ctx
            return "{\"suggestions\": [\"fix1\", \"fix2\", \"fix3\"]}"

    import RobotAid.self_healing_system.kickoff_self_healing as mod
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        mod,
        "OrchestratorAgent",
        lambda locator_agent, app_settings, client_settings, usage_limits=None, **kwargs: SpyOrchestrator(
            locator_agent=locator_agent,
            app_settings=app_settings,
            client_settings=client_settings,
            usage_limits=usage_limits
        ),
    )

    dummy_result = cast(result.Keyword, DummyKeyword())
    app = cast(AppSettings, DummyAppSettings())
    client = cast(ClientSettings, DummyClientSettings())

    resp = KickoffSelfHealing.kickoff_healing(
        result=dummy_result,
        app_settings=app,
        client_settings=client,
        tried_locator_memory=list()
    )
    assert captured['robot_ctx'] == {"failed": True, "tried_locator_memory": []}
    assert captured['locator_agent'].app_settings is app
    assert captured['locator_agent'].client_settings is client
    assert resp == LocatorHealingResponse(suggestions=['fix1', 'fix2', 'fix3'])

    monkeypatch.undo()


def test_kickoff_healing_library_mapping_and_dom_utility() -> None:
    """Test that library mapping works correctly and DOM utility is created."""
    captured_dom_utility_calls = []
    captured_locator_agent_calls = []

    def mock_create_dom_utility(utility_type):
        captured_dom_utility_calls.append(utility_type)
        return f"dom_utility_{utility_type}"
    
    def mock_locator_agent(app_settings, client_settings, usage_limits=None, dom_utility=None, agent_type=None, **kwargs):
        captured_locator_agent_calls.append({
            'app_settings': app_settings,
            'client_settings': client_settings,
            'usage_limits': usage_limits,
            'dom_utility': dom_utility,
            'agent_type': agent_type
        })
        return DummyLocatorAgent(
            app_settings=app_settings,
            client_settings=client_settings,
            usage_limits=usage_limits,
            dom_utility=dom_utility,
            agent_type=agent_type,
        )

    import RobotAid.self_healing_system.kickoff_self_healing as mod
    monkeypatch = pytest.MonkeyPatch()
    
    # Mock RobotCtxRetriever.get_context
    monkeypatch.setattr(
        mod.RobotCtxRetriever,
        "get_context",
        lambda result, dom_utility: {"failed": True},
    )
    
    # Mock DomUtilityFactory.create_dom_utility
    monkeypatch.setattr(
        mod.DomUtilityFactory,
        "create_dom_utility",
        mock_create_dom_utility,
    )
    
    # Mock LocatorAgent
    monkeypatch.setattr(
        mod,
        "LocatorAgent",
        mock_locator_agent,
    )
    
    # Mock OrchestratorAgent
    monkeypatch.setattr(
        mod,
        "OrchestratorAgent",
        lambda locator_agent, app_settings, client_settings, usage_limits=None, **kwargs: DummyOrchestratorAgent(
            locator_agent=locator_agent,
            app_settings=app_settings,
            client_settings=client_settings,
            usage_limits=usage_limits,
        ),
    )
    
    # Mock asyncio.run
    monkeypatch.setattr(
        asyncio,
        "run",
        lambda coro: asyncio.new_event_loop().run_until_complete(coro),
    )

    # Test with Browser library
    dummy_result = cast(result.Keyword, DummyKeyword())
    dummy_result.owner = "Browser"
    dummy_app = cast(AppSettings, DummyAppSettings())
    dummy_client = cast(ClientSettings, DummyClientSettings())

    response = KickoffSelfHealing.kickoff_healing(
        result=dummy_result,
        app_settings=dummy_app,
        client_settings=dummy_client,
        tried_locator_memory=[]
    )

    # Verify DOM utility factory was called with correct agent type
    assert len(captured_dom_utility_calls) == 1
    assert captured_dom_utility_calls[0] == "browser"
    
    # Verify LocatorAgent was called with correct parameters
    assert len(captured_locator_agent_calls) == 1
    locator_call = captured_locator_agent_calls[0]
    assert locator_call['agent_type'] == "browser"
    assert locator_call['dom_utility'] == "dom_utility_browser"
    assert locator_call['app_settings'] is dummy_app
    assert locator_call['client_settings'] is dummy_client
    assert locator_call['usage_limits'] is not None
    
    # Verify response
    assert isinstance(response, LocatorHealingResponse)
    assert response == LocatorHealingResponse(suggestions=['fix1', 'fix2', 'fix3'])

    monkeypatch.undo()


def test_kickoff_healing_unknown_library() -> None:
    """Test behavior with unknown library type."""
    captured_dom_utility_calls = []
    
    def mock_create_dom_utility(utility_type):
        captured_dom_utility_calls.append(utility_type)
        return f"dom_utility_{utility_type}"

    import RobotAid.self_healing_system.kickoff_self_healing as mod
    monkeypatch = pytest.MonkeyPatch()
    
    # Mock all required dependencies
    monkeypatch.setattr(
        mod.RobotCtxRetriever,
        "get_context",
        lambda result, dom_utility: {"failed": True},
    )
    
    monkeypatch.setattr(
        mod.DomUtilityFactory,
        "create_dom_utility",
        mock_create_dom_utility,
    )
    
    monkeypatch.setattr(
        mod,
        "LocatorAgent",
        lambda app_settings, client_settings, usage_limits=None, dom_utility=None, agent_type=None, **kwargs: DummyLocatorAgent(
            app_settings=app_settings,
            client_settings=client_settings,
            usage_limits=usage_limits,
            dom_utility=dom_utility,
            agent_type=agent_type,
        ),
    )
    
    monkeypatch.setattr(
        mod,
        "OrchestratorAgent",
        lambda locator_agent, app_settings, client_settings, usage_limits=None, **kwargs: DummyOrchestratorAgent(
            locator_agent=locator_agent,
            app_settings=app_settings,
            client_settings=client_settings,
            usage_limits=usage_limits,
        ),
    )
    
    monkeypatch.setattr(
        asyncio,
        "run",
        lambda coro: asyncio.new_event_loop().run_until_complete(coro),
    )

    # Test with unknown library
    dummy_result = cast(result.Keyword, DummyKeyword())
    dummy_result.owner = "UnknownLibrary"
    dummy_app = cast(AppSettings, DummyAppSettings())
    dummy_client = cast(ClientSettings, DummyClientSettings())

    response = KickoffSelfHealing.kickoff_healing(
        result=dummy_result,
        app_settings=dummy_app,
        client_settings=dummy_client,
        tried_locator_memory=[]
    )

    # Verify DOM utility factory was called with None (unknown library maps to None)
    assert len(captured_dom_utility_calls) == 1
    assert captured_dom_utility_calls[0] is None
    
    # Verify response is still valid
    assert isinstance(response, LocatorHealingResponse)
    assert response == LocatorHealingResponse(suggestions=['fix1', 'fix2', 'fix3'])

    monkeypatch.undo()
