import pytest
import asyncio
from robot import result
from typing import Any, cast

from RobotAid.utils.app_settings import AppSettings
from RobotAid.utils.client_settings import ClientSettings
from RobotAid.self_healing_system.kickoff_self_healing import KickoffSelfHealing


class DummyKeyword:
    pass


class DummyAppSettings:
    pass


class DummyClientSettings:
    pass


class DummyLocatorAgent:
    def __init__(self, app_settings: Any, client_settings: Any, **kwargs) -> None:
        self.app_settings = app_settings
        self.client_settings = client_settings


class DummyOrchestratorAgent:
    def __init__(self, locator_agent: Any, app_settings: Any, client_settings: Any) -> None:
        self.locator_agent = locator_agent
        self.app_settings = app_settings
        self.client_settings = client_settings

    async def run_async(self, robot_ctx: dict) -> str:
        return "fix1"


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    monkeypatch.setattr(
        "RobotAid.self_healing_system.kickoff_self_healing.RobotCtxRetriever.get_context",
        lambda result: {"failed": True},
    )
    monkeypatch.setattr(
        "RobotAid.self_healing_system.kickoff_self_healing.LocatorAgent",
        lambda app_settings, client_settings, **kwargs: DummyLocatorAgent(
            app_settings=app_settings,
            client_settings=client_settings,
        ),
    )
    monkeypatch.setattr(
        "RobotAid.self_healing_system.kickoff_self_healing.OrchestratorAgent",
        lambda locator_agent, app_settings, client_settings, **kwargs: DummyOrchestratorAgent(
            locator_agent=locator_agent,
            app_settings=app_settings,
            client_settings=client_settings,
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

    assert isinstance(response, str)
    assert response == "fix1"


def test_kickoff_healing_passes_context_and_settings() -> None:
    captured = {}

    class SpyOrchestrator(DummyOrchestratorAgent):
        def __init__(self, locator_agent, app_settings, client_settings) -> None:
            super().__init__(locator_agent=locator_agent,
                             app_settings=app_settings,
                             client_settings=client_settings)
            captured['locator_agent'] = locator_agent
            captured['app_settings'] = app_settings
            captured['client_settings'] = client_settings

        async def run_async(self, robot_ctx):
            captured['robot_ctx'] = robot_ctx
            return ""

    import RobotAid.self_healing_system.kickoff_self_healing as mod
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        mod,
        "OrchestratorAgent",
        lambda locator_agent, app_settings, client_settings, **kwargs: SpyOrchestrator(
            locator_agent=locator_agent,
            app_settings=app_settings,
            client_settings=client_settings
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
    assert resp == ""

    monkeypatch.undo()
