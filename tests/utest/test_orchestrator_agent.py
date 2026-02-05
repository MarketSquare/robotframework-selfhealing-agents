"""Tests for the refactored OrchestratorAgent using Programmatic Hand-Off.

ADR-001d: Orchestrator no longer makes LLM calls. It uses deterministic routing
and delegates directly to the locator agent.
"""
import asyncio
import importlib
import importlib.util
import sys
import types
from typing import Any, Callable, List, Optional, Tuple

import pytest

MODULE_PATH: str = (
    "SelfhealingAgents.self_healing_system.agents.orchestrator_agent.orchestrator_agent"
)


class _LoggerStub:
    def __init__(self) -> None:
        self.infos: List[str] = []

    def info(self, msg: str, also_console: bool = False) -> None:
        self.infos.append(msg)


class _FakeUsageLimits:
    def __init__(self, request_limit: int, total_tokens_limit: int) -> None:
        self.request_limit: int = request_limit
        self.total_tokens_limit: int = total_tokens_limit


class _FakeRunUsage:
    def __init__(self) -> None:
        self.total_tokens: int = 100


def _ensure_module(name: str, builder: Callable[[], types.ModuleType]) -> None:
    existing = sys.modules.get(name)
    try:
        spec = importlib.util.find_spec(name)
    except Exception:
        spec = None
    if spec is None and existing is None:
        sys.modules[name] = builder()
    elif existing is not None:
        parent = name.rpartition(".")[0]
        if parent and parent not in sys.modules:
            pkg = types.ModuleType(parent)
            pkg.__path__ = []
            sys.modules[parent] = pkg


def _ensure_pkg_chain(fullname: str) -> None:
    parts = fullname.split(".")
    for i in range(1, len(parts)):
        pkg = ".".join(parts[:i])
        if pkg not in sys.modules:
            m = types.ModuleType(pkg)
            m.__path__ = []
            sys.modules[pkg] = m


def _stub_robot_logger() -> _LoggerStub:
    logger = _LoggerStub()
    try:
        spec = importlib.util.find_spec("robot.api")
    except Exception:
        spec = None
    if spec is None and "robot.api" not in sys.modules:
        robot_mod = types.ModuleType("robot")
        robot_api_mod = types.ModuleType("robot.api")
        robot_api_mod.logger = logger
        sys.modules["robot"] = robot_mod
        sys.modules["robot.api"] = robot_api_mod
    else:
        mod = sys.modules.get("robot.api") or importlib.import_module("robot.api")
        setattr(mod, "logger", logger)
    return logger


def _install_stubs() -> _LoggerStub:
    def build_pyd_ai_usage() -> types.ModuleType:
        m = types.ModuleType("pydantic_ai.usage")
        m.UsageLimits = _FakeUsageLimits
        m.RunUsage = _FakeRunUsage
        return m

    _ensure_module("pydantic_ai.usage", build_pyd_ai_usage)

    try:
        spec = importlib.util.find_spec("SelfhealingAgents.utils.logging")
    except Exception:
        spec = None
    if spec is None and "SelfhealingAgents.utils.logging" not in sys.modules:
        _ensure_pkg_chain("SelfhealingAgents.utils.logging")
        logging_mod = types.ModuleType("SelfhealingAgents.utils.logging")

        def log(f: Callable[..., Any]) -> Callable[..., Any]:
            return f

        logging_mod.log = log
        sys.modules["SelfhealingAgents.utils.logging"] = logging_mod
    else:
        logging_mod = sys.modules.get(
            "SelfhealingAgents.utils.logging"
        ) or importlib.import_module("SelfhealingAgents.utils.logging")
        if not hasattr(logging_mod, "log"):

            def log(f: Callable[..., Any]) -> Callable[..., Any]:
                return f

            setattr(logging_mod, "log", log)

    mod_name = "SelfhealingAgents.self_healing_system.schemas.api.locator_healing"
    try:
        loc_mod = importlib.import_module(mod_name)
    except Exception:
        loc_mod = None

    def _define_locator_healing_stub() -> None:
        _ensure_pkg_chain(mod_name)
        m = types.ModuleType(mod_name)

        class LocatorHealingResponse:
            def __init__(self, suggestions: List[str]) -> None:
                self.suggestions = suggestions

        class NoHealingNeededResponse:
            def __init__(self, message: str) -> None:
                self.message = message

        m.LocatorHealingResponse = LocatorHealingResponse
        m.NoHealingNeededResponse = NoHealingNeededResponse
        sys.modules[mod_name] = m

    if loc_mod is None:
        _define_locator_healing_stub()
    else:
        if not hasattr(loc_mod, "LocatorHealingResponse") or not hasattr(
            loc_mod, "NoHealingNeededResponse"
        ):
            _define_locator_healing_stub()

    return _stub_robot_logger()


def _import_module_fresh() -> Any:
    if MODULE_PATH in sys.modules:
        del sys.modules[MODULE_PATH]
    return importlib.import_module(MODULE_PATH)


@pytest.fixture()
def orch_setup() -> Tuple[Any, Any, _LoggerStub, Any, Any, Any]:
    logger = _install_stubs()
    mod = _import_module_fresh()
    OrchestratorAgent = getattr(mod, "OrchestratorAgent")
    locator_api = importlib.import_module(
        "SelfhealingAgents.self_healing_system.schemas.api.locator_healing"
    )
    LocatorHealingResponse = getattr(locator_api, "LocatorHealingResponse")
    NoHealingNeededResponse = getattr(locator_api, "NoHealingNeededResponse")
    prompt_payload_mod = importlib.import_module(
        "SelfhealingAgents.self_healing_system.schemas.internal_state.prompt_payload"
    )
    PromptPayload = getattr(prompt_payload_mod, "PromptPayload")
    return mod, OrchestratorAgent, logger, LocatorHealingResponse, NoHealingNeededResponse, PromptPayload


class _FakeLocatorAgent:
    """Mock locator agent for testing orchestrator delegation."""

    def __init__(
        self,
        *,
        is_failed: bool,
        heal_result: Optional[Any] = None,
        raise_on_heal: bool = False,
    ) -> None:
        self._is_failed: bool = is_failed
        self._heal_result: Optional[Any] = heal_result
        self._raise: bool = raise_on_heal
        self.heal_calls: int = 0

    def is_failed_locator_error(self, msg: str) -> bool:
        return self._is_failed

    async def heal_async(
        self,
        payload: Any,
        *,
        usage: Any = None,
        usage_limits: Any = None,
    ) -> Any:
        """Matches the new heal_async signature from ADR-001d."""
        self.heal_calls += 1
        if self._raise:
            raise RuntimeError("heal failed")
        return self._heal_result


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


class FakeCfg:
    """Minimal config for OrchestratorAgent."""
    request_limit: int = 10
    total_tokens_limit: int = 1000


def test_run_async_returns_no_healing_when_not_failed(
    orch_setup: Tuple[Any, Any, _LoggerStub, Any, Any, Any],
) -> None:
    """When is_failed_locator_error returns False, return NoHealingNeededResponse."""
    _, OrchestratorAgent, logger, _, NoHealingNeededResponse, PromptPayload = orch_setup
    logger.infos.clear()

    orch = OrchestratorAgent(FakeCfg(), _FakeLocatorAgent(is_failed=False))
    payload = PromptPayload(
        robot_code_line="Click  #bad",
        error_msg="no failure",
        dom_tree="<body></body>",
        keyword_name="Click",
        keyword_args=("css=#bad",),
        failed_locator="#bad",
        tried_locator_memory=[],
        file_usage_ctx="TestSuite.robot",
    )
    out = _run(orch.run_async(payload))
    assert isinstance(out, NoHealingNeededResponse)
    assert out.message == "no failure"


def test_run_async_delegates_to_locator_agent_on_failure(
    orch_setup: Tuple[Any, Any, _LoggerStub, Any, Any, Any],
) -> None:
    """When is_failed_locator_error returns True, delegate to locator agent."""
    _, OrchestratorAgent, logger, LocatorHealingResponse, _, PromptPayload = orch_setup
    logger.infos.clear()

    heal_response = LocatorHealingResponse(suggestions=["#healed"])
    locator_agent = _FakeLocatorAgent(is_failed=True, heal_result=heal_response)
    orch = OrchestratorAgent(FakeCfg(), locator_agent)

    payload = PromptPayload(
        robot_code_line="Click  #bad",
        error_msg="element not found",
        dom_tree="<body></body>",
        keyword_name="Click",
        keyword_args=("css=#bad",),
        failed_locator="#bad",
        tried_locator_memory=[],
        file_usage_ctx="TestSuite.robot",
    )
    out = _run(orch.run_async(payload))

    assert isinstance(out, LocatorHealingResponse)
    assert out.suggestions == ["#healed"]
    assert locator_agent.heal_calls == 1
    # Should log total tokens
    assert any("total tokens" in msg.lower() for msg in logger.infos)


def test_run_async_logs_token_usage(
    orch_setup: Tuple[Any, Any, _LoggerStub, Any, Any, Any],
) -> None:
    """After successful healing, log the total token usage."""
    _, OrchestratorAgent, logger, LocatorHealingResponse, _, PromptPayload = orch_setup
    logger.infos.clear()

    heal_response = LocatorHealingResponse(suggestions=["#fixed"])
    locator_agent = _FakeLocatorAgent(is_failed=True, heal_result=heal_response)
    orch = OrchestratorAgent(FakeCfg(), locator_agent)

    payload = PromptPayload(
        robot_code_line="Click  #bad",
        error_msg="element not found",
        dom_tree="<body></body>",
        keyword_name="Click",
        keyword_args=("css=#bad",),
        failed_locator="#bad",
        tried_locator_memory=[],
        file_usage_ctx="TestSuite.robot",
    )
    _run(orch.run_async(payload))

    # Verify token usage is logged
    token_logs = [msg for msg in logger.infos if "token" in msg.lower()]
    assert len(token_logs) > 0


def test_orchestrator_uses_usage_limits_from_config(
    orch_setup: Tuple[Any, Any, _LoggerStub, Any, Any, Any],
) -> None:
    """Orchestrator should configure usage limits from cfg."""
    _, OrchestratorAgent, _, _, _, _ = orch_setup

    class CustomCfg:
        request_limit: int = 50
        total_tokens_limit: int = 5000

    locator_agent = _FakeLocatorAgent(is_failed=False)
    orch = OrchestratorAgent(CustomCfg(), locator_agent)

    assert orch._usage_limits.request_limit == 50
    assert orch._usage_limits.total_tokens_limit == 5000


def test_orchestrator_deterministic_routing_no_llm(
    orch_setup: Tuple[Any, Any, _LoggerStub, Any, Any, Any],
) -> None:
    """Verify orchestrator uses Programmatic Hand-Off, not LLM-based delegation."""
    _, OrchestratorAgent, _, _, _, _ = orch_setup

    locator_agent = _FakeLocatorAgent(is_failed=False)
    orch = OrchestratorAgent(FakeCfg(), locator_agent)

    # The new orchestrator should NOT have an _agent attribute (no LLM agent)
    assert not hasattr(orch, "_agent") or orch._agent is None if hasattr(orch, "_agent") else True
    # It should have a _locator_agent instead
    assert hasattr(orch, "_locator_agent")
