import pytest
import asyncio
from typing import Any, cast
from types import SimpleNamespace

from pydantic_ai.usage import UsageLimits

from RobotAid.utils.app_settings import AppSettings
from RobotAid.utils.client_settings import ClientSettings
from RobotAid.self_healing_system.agents.locator_agent import LocatorAgent
from RobotAid.self_healing_system.schemas import PromptPayload, LocatorHealingResponse


class DummyAgentRunResult:
    def __init__(self, output: LocatorHealingResponse) -> None:
        self.output = output


class StubAgent:
    @classmethod
    def __class_getitem__(cls, _args: Any) -> type:
        return cls

    def __init__(
        self,
        model: Any,
        system_prompt: str,
        deps_type: Any,
        output_type: Any
    ) -> None:
        self.model = model
        self.system_prompt = system_prompt
        self.deps_type = deps_type
        self.run_calls: list[tuple[str, Any, Any]] = []
        self.output_type: Any = output_type

    async def run(
        self,
        prompt: str,
        deps: Any,
        usage_limits: Any,
    ) -> DummyAgentRunResult:
        self.run_calls.append((prompt, deps, usage_limits))
        return DummyAgentRunResult(
            output=LocatorHealingResponse(suggestions=["loc1", "loc2", "loc3"])
        )


@pytest.fixture(autouse=True)
def patch_agent_and_model(monkeypatch):
    monkeypatch.setattr(
        "RobotAid.self_healing_system.agents.locator_agent.Agent",
        StubAgent,
    )
    monkeypatch.setattr(
        "RobotAid.self_healing_system.agents.locator_agent.get_model",
        lambda provider, model, client_settings: "fake_model",
    )


def make_app_settings() -> AppSettings:
    stub = SimpleNamespace()
    stub.locator_agent = SimpleNamespace(provider="prov", model="mod")
    return cast(AppSettings, stub)


def make_client_settings() -> ClientSettings:
    return cast(ClientSettings, SimpleNamespace())


def test_agent_initialization_with_custom_limits() -> None:
    app_settings = make_app_settings()
    client_settings = make_client_settings()
    custom_limits = cast(UsageLimits, SimpleNamespace(request_limit=1, total_tokens_limit=100))
    agent = LocatorAgent(
        app_settings=app_settings,
        client_settings=client_settings,
        usage_limits=custom_limits,
    )

    gen = agent.generation_agent
    assert gen.model == "fake_model"
    assert ("You are a helpful assistant for fixing broken locators in the context of robotframework tests."
            in gen.system_prompt)
    assert gen.deps_type is PromptPayload   # type: ignore
    assert agent.usage_limits is custom_limits


def test_default_usage_limits_are_applied() -> None:
    app_settings = make_app_settings()
    client_settings = make_client_settings()
    agent = LocatorAgent(app_settings=app_settings, client_settings=client_settings)

    assert hasattr(agent.usage_limits, "request_limit")
    assert agent.usage_limits.request_limit == 5
    assert agent.usage_limits.total_tokens_limit == 2000


def test_heal_async_uses_generation_agent_run() -> None:
    app_settings = make_app_settings()
    client_settings = make_client_settings()
    agent = LocatorAgent(app_settings=app_settings, client_settings=client_settings)

    payload = PromptPayload(
        robot_code_line="Click Button id=btn",
        error_msg="NoSuchElementError",
        dom_tree="btn-loc1 btn-loc2 btn-loc3",
        tried_locator_memory=[]
    )
    ctx = SimpleNamespace(deps=payload)

    result = asyncio.new_event_loop().run_until_complete(agent.heal_async(ctx))     # type: ignore

    assert result == LocatorHealingResponse(suggestions=["loc1", "loc2", "loc3"])

    run_calls = agent.generation_agent.run_calls    # type: ignore
    assert len(run_calls) == 1
    prompt_passed, deps_passed, usage_passed = run_calls[0]
    assert ((f"You are given a Robot Framework keyword that failed due to an inaccessible locator. "
            f"Using the elements in the DOM at failure time, suggest 3 new locators. "
            f"You are also given a list of tried locator suggestions memory that were tried but still failed. "
            f"Make sure you do not suggest a locator that is on that list. "
            f"Note: Only respond with the locators, do not give any additional information in any case.\n\n")
            in prompt_passed)
    assert deps_passed is payload
    assert usage_passed == agent.usage_limits
