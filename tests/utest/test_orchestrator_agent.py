import sys
import types
import pytest
import asyncio
import importlib
import importlib.util
from typing import Any, Callable, List, Optional, Tuple


MODULE_PATH: str = "RobotAid.self_healing_system.agents.orchestrator_agent.orchestrator_agent"


class _LoggerStub:
    def __init__(self) -> None:
        self.infos: List[str] = []
    def info(self, msg: str) -> None:
        self.infos.append(msg)


class _FakeAgentRunResult:
    def __init__(self, output: str) -> None:
        self.output: str = output


class _FakeUsageLimits:
    def __init__(self, req: int, total: int) -> None:
        self.request_limit: int = req
        self.total_tokens_limit: int = total


class _FakeAgent:
    instances: List["_FakeAgent"] = []
    def __init__(self, *, model: Any, system_prompt: str, deps_type: Any, output_type: Any) -> None:
        self.model = model
        self.system_prompt = system_prompt
        self.deps_type = deps_type
        self.output_type = output_type
        self.run_calls: int = 0
        self.run_result: _FakeAgentRunResult = _FakeAgentRunResult("default")
        _FakeAgent.instances.append(self)
    @classmethod
    def __class_getitem__(cls, item: Any) -> "_FakeAgent":
        return cls
    async def run(self, prompt: str, *, deps: Any, usage_limits: Any, model_settings: Any) -> _FakeAgentRunResult:
        self.run_calls += 1
        return self.run_result


class _FakeModelRetry(Exception):
    pass


class _FakeRunContext:
    def __init__(self, deps: Any = None) -> None:
        self.deps: Any = deps


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
    def build_pyd_ai() -> types.ModuleType:
        m = types.ModuleType("pydantic_ai")
        m.Agent = _FakeAgent
        m.ModelRetry = _FakeModelRetry
        m.RunContext = _FakeRunContext
        return m
    def build_pyd_ai_usage() -> types.ModuleType:
        m = types.ModuleType("pydantic_ai.usage")
        m.UsageLimits = _FakeUsageLimits
        return m
    def build_pyd_ai_agent() -> types.ModuleType:
        m = types.ModuleType("pydantic_ai.agent")
        m.AgentRunResult = _FakeAgentRunResult
        return m

    _ensure_module("pydantic_ai", build_pyd_ai)
    _ensure_module("pydantic_ai.usage", build_pyd_ai_usage)
    _ensure_module("pydantic_ai.agent", build_pyd_ai_agent)

    try:
        spec = importlib.util.find_spec("RobotAid.utils.logging")
    except Exception:
        spec = None
    if spec is None and "RobotAid.utils.logging" not in sys.modules:
        _ensure_pkg_chain("RobotAid.utils.logging")
        logging_mod = types.ModuleType("RobotAid.utils.logging")
        def log(f: Callable[..., Any]) -> Callable[..., Any]:
            return f
        logging_mod.log = log
        sys.modules["RobotAid.utils.logging"] = logging_mod
    else:
        logging_mod = sys.modules.get("RobotAid.utils.logging") or importlib.import_module("RobotAid.utils.logging")
        if not hasattr(logging_mod, "log"):
            def log(f: Callable[..., Any]) -> Callable[..., Any]:
                return f
            setattr(logging_mod, "log", log)

    mod_name = "RobotAid.self_healing_system.schemas.api.locator_healing"
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
        if not hasattr(loc_mod, "LocatorHealingResponse") or not hasattr(loc_mod, "NoHealingNeededResponse"):
            _define_locator_healing_stub()

    return _stub_robot_logger()


def _import_module_fresh() -> Any:
    if MODULE_PATH in sys.modules:
        del sys.modules[MODULE_PATH]
    return importlib.import_module(MODULE_PATH)


@pytest.fixture()
def orch_setup() -> Tuple[Any, Any, _LoggerStub, Any, Any]:
    logger = _install_stubs()
    mod = _import_module_fresh()
    OrchestratorAgent = getattr(mod, "OrchestratorAgent")
    locator_api = importlib.import_module("RobotAid.self_healing_system.schemas.api.locator_healing")
    NoHealingNeededResponse = getattr(locator_api, "NoHealingNeededResponse")
    prompt_payload_mod = importlib.import_module("RobotAid.self_healing_system.schemas.internal_state.prompt_payload")
    PromptPayload = getattr(prompt_payload_mod, "PromptPayload")
    return mod, OrchestratorAgent, logger, NoHealingNeededResponse, PromptPayload


class _FakeLocatorAgent:
    def __init__(self, *, is_failed: bool, heal_result: Optional[str] = None, raise_on_heal: bool = False) -> None:
        self._is_failed: bool = is_failed
        self._heal_result: Optional[str] = heal_result
        self._raise: bool = raise_on_heal
    def is_failed_locator_error(self, msg: str) -> bool:
        return self._is_failed
    async def heal_async(self, ctx: Any) -> str:
        if self._raise:
            raise RuntimeError("heal failed")
        return self._heal_result or '{"suggestions":[]}'


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def test_run_async_returns_no_healing_when_not_failed(orch_setup: Tuple[Any, Any, _LoggerStub, Any, Any]) -> None:
    _, OrchestratorAgent, logger, NoHealingNeededResponse, PromptPayload = orch_setup
    _FakeAgent.instances.clear()
    logger.infos.clear()
    class FakeCfg:
        request_limit: int = 10
        total_tokens_limit: int = 1000
        orchestrator_agent_provider: str = "prov"
        orchestrator_agent_model: str = "mod"
    orch = OrchestratorAgent(FakeCfg(), _FakeLocatorAgent(is_failed=False))
    payload = PromptPayload(
        robot_code_line="Click  #bad",
        error_msg="no failure",
        dom_tree="<body></body>",
        keyword_name="Click",
        keyword_args=("css=#bad",),
        failed_locator="#bad",
        tried_locator_memory=[],
    )
    out = _run(orch.run_async(payload))
    assert isinstance(out, NoHealingNeededResponse)
    assert out.message == "no failure"
    assert (len(_FakeAgent.instances) == 0) or (_FakeAgent.instances[0].run_calls == 0)
    assert logger.infos == []


def test_run_async_calls_agent_and_logs_on_error(orch_setup: Tuple[Any, Any, _LoggerStub, Any, Any]) -> None:
    _, OrchestratorAgent, logger, _, PromptPayload = orch_setup
    _FakeAgent.instances.clear()
    logger.infos.clear()
    class FakeCfg:
        request_limit: int = 10
        total_tokens_limit: int = 1000
        orchestrator_agent_provider: str = "prov"
        orchestrator_agent_model: str = "mod"
    orch = OrchestratorAgent(FakeCfg(), _FakeLocatorAgent(is_failed=True))
    payload = PromptPayload(
        robot_code_line="Click  #bad",
        error_msg="boom",
        dom_tree="<body></body>",
        keyword_name="Click",
        keyword_args=("css=#bad",),
        failed_locator="#bad",
        tried_locator_memory=[],
    )
    if _FakeAgent.instances:
        _FakeAgent.instances[0].run_result = _FakeAgentRunResult("error: token limit")
    else:
        class StubAgent:
            async def run(self, *args: Any, **kwargs: Any) -> _FakeAgentRunResult:
                return _FakeAgentRunResult("error: token limit")
        orch._agent = StubAgent()
    out = _run(orch.run_async(payload))
    assert out == "error: token limit"
    assert logger.infos == ["error: token limit"]
    if _FakeAgent.instances:
        assert _FakeAgent.instances[0].run_calls == 1


def test_run_async_calls_agent_no_log_when_ok(orch_setup: Tuple[Any, Any, _LoggerStub, Any, Any]) -> None:
    _, OrchestratorAgent, logger, _, PromptPayload = orch_setup
    _FakeAgent.instances.clear()
    logger.infos.clear()
    class FakeCfg:
        request_limit: int = 10
        total_tokens_limit: int = 1000
        orchestrator_agent_provider: str = "prov"
        orchestrator_agent_model: str = "mod"
    orch = OrchestratorAgent(FakeCfg(), _FakeLocatorAgent(is_failed=True))
    payload = PromptPayload(
        robot_code_line="Click  #bad",
        error_msg="boom",
        dom_tree="<body></body>",
        keyword_name="Click",
        keyword_args=("css=#bad",),
        failed_locator="#bad",
        tried_locator_memory=[],
    )
    if _FakeAgent.instances:
        _FakeAgent.instances[0].run_result = _FakeAgentRunResult("all good")
    else:
        class StubAgent:
            async def run(self, *args: Any, **kwargs: Any) -> _FakeAgentRunResult:
                return _FakeAgentRunResult("all good")
        orch._agent = StubAgent()
    out = _run(orch.run_async(payload))
    assert out == "all good"
    assert logger.infos == []
    if _FakeAgent.instances:
        assert _FakeAgent.instances[0].run_calls == 1


def test_get_healed_locators_success(orch_setup: Tuple[Any, Any, _LoggerStub, Any, Any]) -> None:
    _, OrchestratorAgent, _, __, ___ = orch_setup
    class FakeCfg:
        request_limit: int = 10
        total_tokens_limit: int = 1000
        orchestrator_agent_provider: str = "prov"
        orchestrator_agent_model: str = "mod"
    orch = OrchestratorAgent(FakeCfg(), _FakeLocatorAgent(is_failed=True, heal_result='{"suggestions":["#ok"]}'))
    out = _run(orch._get_healed_locators(_FakeRunContext(deps=None)))
    assert out == '{"suggestions":["#ok"]}'


def test_get_healed_locators_raises_modelretry(orch_setup: Tuple[Any, Any, _LoggerStub, Any, Any]) -> None:
    _, OrchestratorAgent, _, __, ___ = orch_setup
    ModelRetry = importlib.import_module("pydantic_ai").ModelRetry
    class FakeCfg:
        request_limit: int = 10
        total_tokens_limit: int = 1000
        orchestrator_agent_provider: str = "prov"
        orchestrator_agent_model: str = "mod"
    orch = OrchestratorAgent(FakeCfg(), _FakeLocatorAgent(is_failed=True, raise_on_heal=True))
    with pytest.raises(ModelRetry):
        _run(orch._get_healed_locators(_FakeRunContext(deps=None)))


def test_catch_token_limit_exceedance_logs(orch_setup: Tuple[Any, Any, _LoggerStub, Any, Any]) -> None:
    _, OrchestratorAgent, logger, __, ___ = orch_setup
    logger.infos.clear()
    OrchestratorAgent._catch_token_limit_exceedance("error: out of tokens")
    assert logger.infos == ["error: out of tokens"]
    logger.infos.clear()
    OrchestratorAgent._catch_token_limit_exceedance("ok")
    assert logger.infos == []
