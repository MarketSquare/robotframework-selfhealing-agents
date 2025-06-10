import pytest
import asyncio
from typing import Any, cast
from types import SimpleNamespace

from RobotAid.utils.app_settings import AppSettings
from RobotAid.utils.client_settings import ClientSettings
from RobotAid.self_healing_system.agents.orchestrator_agent import OrchestratorAgent
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
        self.tools = {}
        self.run_calls = []
        self.output_type = output_type

    def tool(self, name: str) -> Any:
        def decorator(fn: Any) -> Any:
            self.tools[name] = fn
            return fn
        return decorator

    async def run(
        self,
        prompt: str,
        deps: Any,
        usage_limits: Any,
    ) -> DummyAgentRunResult:
        self.run_calls.append((prompt, deps, usage_limits))
        return DummyAgentRunResult(
            output=LocatorHealingResponse(suggestions=["out1", "out2", "out3"])
        )


@pytest.fixture(autouse=True)
def patch_agent_and_model(monkeypatch):
    monkeypatch.setattr(
        "RobotAid.self_healing_system.agents.orchestrator_agent.Agent",
        StubAgent,
    )
    monkeypatch.setattr(
        "RobotAid.self_healing_system.agents.orchestrator_agent.get_model",
        lambda provider, model, client_settings: "fake_model",
    )


def make_app_settings() -> AppSettings:
    stub = SimpleNamespace()
    stub.orchestrator_agent = SimpleNamespace(provider="prov", model="mod")
    return cast(AppSettings, stub)


def make_client_settings() -> ClientSettings:
    return cast(ClientSettings, SimpleNamespace())


def make_locator_agent() -> Any:
    class StubLocatorAgent:
        async def heal_async(self, ctx: Any) -> LocatorHealingResponse:
            return LocatorHealingResponse(suggestions=["suggA", "suggB", "suggC"])
    return StubLocatorAgent()


def test_tool_registration_and_invocation() -> None:
    app_settings = make_app_settings()
    client_settings = make_client_settings()
    locator_agent = make_locator_agent()

    orch = OrchestratorAgent(
        app_settings=app_settings,
        client_settings=client_settings,
        locator_agent=locator_agent,
    )

    assert "locator_heal" in orch.agent.tools   # type: ignore

    tool_fn = orch.agent.tools["locator_heal"]  # type: ignore
    payload = PromptPayload(robot_code_line="keyword call", error_msg="err", dom_tree="i1")
    ctx = SimpleNamespace(deps=payload)
    result = asyncio.new_event_loop().run_until_complete(tool_fn(ctx))

    assert isinstance(result, LocatorHealingResponse)
    assert result == LocatorHealingResponse(suggestions=["suggA", "suggB", "suggC"])


def test_run_async_calls_agent_run_and_returns_output() -> None:
    app_settings = make_app_settings()
    client_settings = make_client_settings()
    locator_agent = make_locator_agent()

    orch = OrchestratorAgent(
        app_settings=app_settings,
        client_settings=client_settings,
        locator_agent=locator_agent,
    )

    robot_ctx = {"robot_code_line": "keyword call", "error_msg": "err", "dom_tree": "i1"}
    result = asyncio.new_event_loop().run_until_complete(
        orch.run_async(robot_ctx=robot_ctx)
    )

    assert isinstance(result, LocatorHealingResponse)
    assert result == LocatorHealingResponse(suggestions=["out1", "out2", "out3"])

    assert len(orch.agent.run_calls) == 1   # type: ignore
    prompt, deps, usage = orch.agent.run_calls[0]   # type: ignore
    assert prompt == ("Please call the tool 'locator_heal'. Only respond with the message the tool gave you, do "
                      "not add any additional information in any case.")
    assert isinstance(deps, PromptPayload)
    assert deps.error_msg == "err"
    assert deps.dom_tree == "i1"
    assert hasattr(usage, "request_limit") and usage.request_limit == 5
    assert hasattr(usage, "total_tokens_limit") and usage.total_tokens_limit == 2000
