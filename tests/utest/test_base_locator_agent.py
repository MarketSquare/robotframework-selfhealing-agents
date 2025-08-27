import sys
import types
import pytest
import asyncio
import importlib
from typing import Any, Callable, List, Optional, Tuple


MODULE_PATH: str = "SelfhealingAgents.self_healing_system.agents.locator_agent.base_locator_agent"


def _run(coro):
    return asyncio.run(coro)


class _LoggerStub:
    def __init__(self) -> None:
        self.infos: List[str] = []
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.infos.append(str(msg))


class _FakeAgentRunResult:
    def __init__(self, output: Any) -> None:
        self.output: Any = output


class _FakeUsageLimits:
    def __init__(self, req: int, total: int) -> None:
        self.request_limit: int = req
        self.total_tokens_limit: int = total


class _FakeAgent:
    def __init__(self, *, model: Any, system_prompt: str, deps_type: Any, output_type: Any) -> None:
        self.model = model
        self.system_prompt = system_prompt
        self.deps_type = deps_type
        self.output_type = output_type
        self.run_result: _FakeAgentRunResult = _FakeAgentRunResult(None)
        self.validator: Optional[Callable[..., Any]] = None
        self.run_calls: int = 0
    @classmethod
    def __class_getitem__(cls, item: Any) -> "_FakeAgent":
        return cls
    def output_validator(self, func: Callable[..., Any]) -> Callable[..., Any]:
        self.validator = func
        return func
    async def run(self, *args: Any, **kwargs: Any) -> _FakeAgentRunResult:
        self.run_calls += 1
        return self.run_result


class _FakeModelRetry(Exception):
    pass


class _FakeRunContext:
    def __init__(self, deps: Any) -> None:
        self.deps: Any = deps

    @classmethod
    def __class_getitem__(cls, item: Any) -> "._FakeRunContext":
        return cls


def _force_module(name: str, module: types.ModuleType) -> None:
    sys.modules[name] = module


def _install_stubs() -> _LoggerStub:
    robot_mod = types.ModuleType("robot")
    robot_mod.__path__ = []
    robot_api_mod = types.ModuleType("robot.api")
    robot_api_mod.__path__ = []
    robot_api_interfaces_mod = types.ModuleType("robot.api.interfaces")
    class ListenerV3: ...
    robot_api_interfaces_mod.ListenerV3 = ListenerV3
    logger = _LoggerStub()
    robot_api_mod.logger = logger
    _force_module("robot", robot_mod)
    _force_module("robot.api", robot_api_mod)
    _force_module("robot.api.interfaces", robot_api_interfaces_mod)
    _force_module("robot.result", types.ModuleType("robot.result"))
    _force_module("robot.running", types.ModuleType("robot.running"))

    listener_stub = types.ModuleType("SelfhealingAgents.listener")
    class SelfhealingAgents: ...
    listener_stub.SelfhealingAgents = SelfhealingAgents
    _force_module("SelfhealingAgents.listener", listener_stub)

    pa = types.ModuleType("pydantic_ai")
    pa.Agent = _FakeAgent
    pa.ModelRetry = _FakeModelRetry
    pa.RunContext = _FakeRunContext
    _force_module("pydantic_ai", pa)

    pa_usage = types.ModuleType("pydantic_ai.usage")
    pa_usage.UsageLimits = _FakeUsageLimits
    _force_module("pydantic_ai.usage", pa_usage)

    pa_agent = types.ModuleType("pydantic_ai.agent")
    pa_agent.AgentRunResult = _FakeAgentRunResult
    _force_module("pydantic_ai.agent", pa_agent)

    aid_utils = types.ModuleType("SelfhealingAgents.utils")
    logging_mod = types.ModuleType("SelfhealingAgents.utils.logging")
    def log(f: Callable[..., Any]) -> Callable[..., Any]:
        return f
    logging_mod.log = log
    cfg_mod = types.ModuleType("SelfhealingAgents.utils.cfg")
    class Cfg:
        def __init__(self) -> None:
            self.request_limit: int = 10
            self.total_tokens_limit: int = 1000
            self.use_llm_for_locator_generation: bool = True
            self.locator_agent_provider: str = "prov"
            self.locator_agent_model: str = "mod"
    cfg_mod.Cfg = Cfg
    _force_module("SelfhealingAgents.utils", aid_utils)
    _force_module("SelfhealingAgents.utils.logging", logging_mod)
    _force_module("SelfhealingAgents.utils.cfg", cfg_mod)

    prompts_pkg = types.ModuleType("SelfhealingAgents.self_healing_system.agents.prompts.locator.prompts_locator")
    class PromptsLocatorGenerationAgent:
        @staticmethod
        def get_system_msg(dom: Any) -> str:
            return "GEN_SYS"
        @staticmethod
        def get_user_msg(ctx: Any) -> str:
            return "GEN_USER"
    class PromptsLocatorSelectionAgent:
        @staticmethod
        def get_system_msg() -> str:
            return "SEL_SYS"
        @staticmethod
        def get_user_msg(ctx: Any, suggestions: List[str], metadata: List[dict]) -> str:
            return "SEL_USER"
    prompts_pkg.PromptsLocatorGenerationAgent = PromptsLocatorGenerationAgent
    prompts_pkg.PromptsLocatorSelectionAgent = PromptsLocatorSelectionAgent
    _force_module("SelfhealingAgents.self_healing_system.agents.prompts.locator.prompts_locator", prompts_pkg)

    client_model = types.ModuleType("SelfhealingAgents.self_healing_system.llm.client_model")
    def get_client_model(provider: str, model: str, cfg: Any) -> str:
        return f"{provider}:{model}"
    client_model.get_client_model = get_client_model
    _force_module("SelfhealingAgents.self_healing_system.llm.client_model", client_model)

    loc_schema = types.ModuleType("SelfhealingAgents.self_healing_system.schemas.api.locator_healing")
    class LocatorHealingResponse:
        def __init__(self, suggestions: List[str]) -> None:
            self.suggestions: List[str] = suggestions
    loc_schema.LocatorHealingResponse = LocatorHealingResponse
    _force_module("SelfhealingAgents.self_healing_system.schemas.api.locator_healing", loc_schema)

    payload_mod = types.ModuleType("SelfhealingAgents.self_healing_system.schemas.internal_state.prompt_payload")
    class PromptPayload:
        def __init__(
            self,
            robot_code_line: str,
            error_msg: str,
            dom_tree: str,
            keyword_name: str,
            keyword_args: tuple,
            failed_locator: str,
            tried_locator_memory: list,
        ) -> None:
            self.robot_code_line = robot_code_line
            self.error_msg = error_msg
            self.dom_tree = dom_tree
            self.keyword_name = keyword_name
            self.keyword_args = keyword_args
            self.failed_locator = failed_locator
            self.tried_locator_memory = tried_locator_memory
    payload_mod.PromptPayload = PromptPayload
    _force_module("SelfhealingAgents.self_healing_system.schemas.internal_state.prompt_payload", payload_mod)

    base_dom = types.ModuleType("SelfhealingAgents.self_healing_system.context_retrieving.library_dom_utils.base_dom_utils")
    class BaseDomUtils: ...
    base_dom.BaseDomUtils = BaseDomUtils
    _force_module("SelfhealingAgents.self_healing_system.context_retrieving.library_dom_utils.base_dom_utils", base_dom)

    return logger


def _import_module_fresh() -> Any:
    if MODULE_PATH in sys.modules:
        del sys.modules[MODULE_PATH]
    return importlib.import_module(MODULE_PATH)


@pytest.fixture()
def mod_and_cls() -> Tuple[Any, Any, Any, Any]:
    logger = _install_stubs()
    mod = _import_module_fresh()
    BaseLocatorAgent = getattr(mod, "BaseLocatorAgent")
    LocatorHealingResponse = importlib.import_module(
        "SelfhealingAgents.self_healing_system.schemas.api.locator_healing"
    ).LocatorHealingResponse
    PromptPayload = importlib.import_module(
        "SelfhealingAgents.self_healing_system.schemas.internal_state.prompt_payload"
    ).PromptPayload
    return BaseLocatorAgent, LocatorHealingResponse, PromptPayload, logger


class _DomStub:
    def __init__(
        self,
        *,
        proposals: List[str] | None = None,
        valid: bool = True,
        unique_map: Optional[dict] = None,
        clickable_map: Optional[dict] = None,
        metadata_map: Optional[dict] = None,
        raise_valid: bool = False,
        raise_unique: bool = False,
        raise_clickable: bool = False,
    ) -> None:
        self._proposals = proposals or []
        self._valid = valid
        self._unique_map = unique_map or {}
        self._clickable_map = clickable_map or {}
        self._metadata_map = metadata_map or {}
        self._raise_valid = raise_valid
        self._raise_unique = raise_unique
        self._raise_clickable = raise_clickable
    def get_locator_proposals(self, failed: str, keyword: str) -> List[str]:
        return list(self._proposals)
    def get_locator_metadata(self, locator: str) -> List[dict]:
        return [self._metadata_map.get(locator, {"id": locator})]
    def is_locator_valid(self, locator: str) -> bool:
        if self._raise_valid:
            raise RuntimeError("valid err")
        return self._valid
    def is_locator_unique(self, locator: str) -> bool:
        if self._raise_unique:
            raise RuntimeError("unique err")
        return bool(self._unique_map.get(locator, False))
    def is_element_clickable(self, locator: str) -> bool:
        if self._raise_clickable:
            raise RuntimeError("click err")
        return bool(self._clickable_map.get(locator, False))


def _payload(PromptPayload: Any, *, keyword: str = "Click") -> Any:
    return PromptPayload(
        robot_code_line="KW  #bad",
        error_msg="boom",
        dom_tree="<body/>",
        keyword_name=keyword,
        keyword_args=("css=#bad",),
        failed_locator="#bad",
        tried_locator_memory=[],
    )


def _ctx(payload: Any) -> Any:
    return _FakeRunContext(deps=payload)


class _ConcreteAgentFactory:
    @staticmethod
    def make(BaseLocatorAgent: Any, dom: _DomStub, *, use_llm: bool) -> Any:
        class Impl(BaseLocatorAgent):
            def _process_locator(self, locator: str) -> str:
                return f"proc:{locator}"
            @staticmethod
            def is_failed_locator_error(message: str) -> bool:
                return "failed" in message.lower()
        class Cfg:
            request_limit: int = 9
            total_tokens_limit: int = 999
            use_llm_for_locator_generation: bool = use_llm
            locator_agent_provider: str = "prov"
            locator_agent_model: str = "mod"
        return Impl(Cfg(), dom)


def test_init_configures_agents_by_mode(mod_and_cls: Tuple[Any, Any, Any, Any]) -> None:
    BaseLocatorAgent, _, __, ___ = mod_and_cls
    dom = _DomStub(valid=True)
    inst_llm = _ConcreteAgentFactory.make(BaseLocatorAgent, dom, use_llm=True)
    assert inst_llm.generation_agent is not None
    assert inst_llm.selection_agent is None
    assert callable(getattr(inst_llm.generation_agent, "validator", None))
    inst_dom = _ConcreteAgentFactory.make(BaseLocatorAgent, dom, use_llm=False)
    assert inst_dom.generation_agent is None
    assert inst_dom.selection_agent is not None


def test_output_validator_processes_and_filters(mod_and_cls: Tuple[Any, Any, Any, Any]) -> None:
    BaseLocatorAgent, LocatorHealingResponse, PromptPayload, _ = mod_and_cls
    dom = _DomStub(
        valid=True,
        unique_map={"proc:a": True, "proc:b": False},
        clickable_map={"proc:a": True, "proc:b": False},
    )
    inst = _ConcreteAgentFactory.make(BaseLocatorAgent, dom, use_llm=True)
    val = inst.generation_agent.validator
    out = LocatorHealingResponse(["a", "b"])
    res = _run(val(_ctx(_payload(PromptPayload, keyword="Click")), out))
    assert isinstance(res, LocatorHealingResponse)
    assert res.suggestions == ["proc:a"]
    with pytest.raises(_FakeModelRetry):
        _run(val(_ctx(_payload(PromptPayload, keyword="Click")), LocatorHealingResponse([])))


def test_heal_with_llm_success_and_type_check(mod_and_cls: Tuple[Any, Any, Any, Any]) -> None:
    BaseLocatorAgent, LocatorHealingResponse, PromptPayload, _ = mod_and_cls
    dom = _DomStub(valid=True)
    inst = _ConcreteAgentFactory.make(BaseLocatorAgent, dom, use_llm=True)
    inst.generation_agent.run_result = _FakeAgentRunResult(LocatorHealingResponse(["x"]))
    out = _run(inst._heal_with_llm(_ctx(_payload(PromptPayload))))
    assert isinstance(out, LocatorHealingResponse)
    assert out.suggestions == ["x"]
    inst.generation_agent.run_result = _FakeAgentRunResult("bad")
    with pytest.raises(_FakeModelRetry):
        _run(inst._heal_with_llm(_ctx(_payload(PromptPayload))))


def test_heal_with_dom_utils_json_and_raw_selection(mod_and_cls: Tuple[Any, Any, Any, Any]) -> None:
    BaseLocatorAgent, LocatorHealingResponse, PromptPayload, _ = mod_and_cls
    dom = _DomStub(
        proposals=["l2", "l1"],
        valid=True,
        unique_map={"proc:l1": True, "proc:l2": False},
        clickable_map={"proc:l1": True, "proc:l2": True},
    )
    inst = _ConcreteAgentFactory.make(BaseLocatorAgent, dom, use_llm=False)
    inst.selection_agent.run_result = _FakeAgentRunResult('{"suggestions":"#best"}')
    out = _run(inst._heal_with_dom_utils(_ctx(_payload(PromptPayload, keyword="Click"))))
    assert isinstance(out, LocatorHealingResponse)
    assert out.suggestions == ["#best"]
    inst.selection_agent.run_result = _FakeAgentRunResult("#alt")
    out2 = _run(inst._heal_with_dom_utils(_ctx(_payload(PromptPayload, keyword="Click"))))
    assert out2.suggestions == ["#alt"]


def test_heal_with_dom_utils_empty_proposals_raises(mod_and_cls: Tuple[Any, Any, Any, Any]) -> None:
    BaseLocatorAgent, _, PromptPayload, _ = mod_and_cls
    dom = _DomStub(proposals=[], valid=True)
    inst = _ConcreteAgentFactory.make(BaseLocatorAgent, dom, use_llm=False)
    with pytest.raises(_FakeModelRetry):
        _run(inst._heal_with_dom_utils(_ctx(_payload(PromptPayload))))


def test_is_locator_valid_unique_clickable_with_exceptions(mod_and_cls: Tuple[Any, Any, Any, Any]) -> None:
    BaseLocatorAgent, _, __, ___ = mod_and_cls
    dom = _DomStub(valid=True, unique_map={"proc:x": True}, clickable_map={"proc:x": True})
    inst = _ConcreteAgentFactory.make(BaseLocatorAgent, dom, use_llm=False)
    assert inst._is_locator_valid("proc:x") is True
    assert inst._is_locator_unique("proc:x") is True
    assert inst._is_element_clickable("proc:x") is True
    dom_exc = _DomStub(raise_valid=True, raise_unique=True, raise_clickable=True)
    inst2 = _ConcreteAgentFactory.make(BaseLocatorAgent, dom_exc, use_llm=False)
    assert inst2._is_locator_valid("x") is False
    assert inst2._is_locator_unique("x") is False
    assert inst2._is_element_clickable("x") is False


def test_sort_and_filter_helpers(mod_and_cls: Tuple[Any, Any, Any, Any]) -> None:
    BaseLocatorAgent, _, __, ___ = mod_and_cls
    dom = _DomStub(
        valid=True,
        unique_map={"a": True, "b": False, "c": True},
        clickable_map={"a": True, "b": False, "c": True},
    )
    inst = _ConcreteAgentFactory.make(BaseLocatorAgent, dom, use_llm=False)
    sorted_list = inst._sort_locators(["b", "a", "c"])
    assert sorted_list[:2] == ["a", "c"]
    filtered = inst._filter_clickable_locators(["a", "b", "c"])
    assert filtered == ["a", "c"]
