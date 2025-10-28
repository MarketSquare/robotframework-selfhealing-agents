import importlib
from dataclasses import dataclass
from typing import Any, List, Optional


MODULE_PATH: str = "SelfhealingAgents.self_healing_system.context_retrieving.robot_ctx_retriever"
robot_ctx_module = importlib.import_module(MODULE_PATH)
RobotCtxRetriever = getattr(robot_ctx_module, "RobotCtxRetriever")


@dataclass
class FakeData:
    file_usage_ctx: str

@dataclass
class FakeKeyword:
    name: str
    args: List[Any]
    message: str
    assign: Optional[List[str]] = None


class FakeDomUtils:
    def __init__(self, dom: str) -> None:
        self._dom: str = dom
        self.get_dom_tree_calls: int = 0

    def get_dom_tree(self) -> str:
        self.get_dom_tree_calls += 1
        return self._dom


class DummyBuiltIn:
    def __init__(self) -> None:
        self.calls: List[Any] = []

    def replace_variables(self, value: Any) -> str:
        self.calls.append(value)
        return f"LOC::{value}"


@dataclass
class FakePromptPayload:
    robot_code_line: str
    error_msg: str
    dom_tree: str
    keyword_name: str
    keyword_args: List[Any]
    failed_locator: Any
    tried_locator_memory: List[Any]
    locator_type: str
    file_usage_ctx: str


def fake_seq2str(items: List[Any], quote: str = "", sep: str = " ", lastsep: str = " ") -> str:
    return sep.join(str(x) for x in items) + lastsep


def _fake_file_usage_ctx(data: Any) -> str:
    return getattr(data, "file_usage_ctx", "")


def patch_module_symbols(monkeypatch: Any) -> DummyBuiltIn:
    monkeypatch.setattr(robot_ctx_module, "seq2str", fake_seq2str, raising=True)
    builtin_stub = DummyBuiltIn()
    monkeypatch.setattr(robot_ctx_module, "BuiltIn", lambda: builtin_stub, raising=True)
    monkeypatch.setattr(robot_ctx_module, "PromptPayload", FakePromptPayload, raising=True)
    monkeypatch.setattr(RobotCtxRetriever, "_file_usage_ctx", staticmethod(_fake_file_usage_ctx), raising=True)
    return builtin_stub


def test_format_keyword_call_without_assign(monkeypatch: Any) -> None:
    patch_module_symbols(monkeypatch)
    kw: FakeKeyword = FakeKeyword(
        name="Click Element",
        args=["${locator}", "timeout=5"],
        message="x"
    )
    out: str = RobotCtxRetriever._format_keyword_call(kw)
    assert out == "Click Element ${locator} timeout=5 "


def test_format_keyword_call_with_assign(monkeypatch: Any) -> None:
    patch_module_symbols(monkeypatch)
    kw: FakeKeyword = FakeKeyword(
        assign=["${res1}", "${res2}"],
        name="Do Stuff",
        args=["a", "b"],
        message="x"
    )
    out: str = RobotCtxRetriever._format_keyword_call(kw)
    assert out == "${res1} = ${res2} = Do Stuff a b "


def test_get_context_payload_builds_expected_payload(monkeypatch: Any) -> None:
    builtin_stub: DummyBuiltIn = patch_module_symbols(monkeypatch)
    dom_util: FakeDomUtils = FakeDomUtils("<DOM/>")

    data: FakeData = FakeData(
        file_usage_ctx="TestSuiteDummyString",
    )

    kw: FakeKeyword = FakeKeyword(
        name="Click Element",
        args=["${btn}", "timeout=5"],
        message="Element not found"
    )

    payload: FakePromptPayload = RobotCtxRetriever.get_context_payload(
        data, kw, dom_util
    )

    assert payload.robot_code_line == "Click Element ${btn} timeout=5 "
    assert payload.error_msg == "Element not found"
    assert payload.dom_tree == "<DOM/>"
    assert payload.keyword_name == "Click Element"
    assert payload.keyword_args == ["${btn}", "timeout=5"]
    assert payload.failed_locator == "LOC::${btn}"
    assert payload.tried_locator_memory == []
    assert dom_util.get_dom_tree_calls == 1
    assert builtin_stub.calls == ["${btn}"]
    assert payload.locator_type == "tbd"
    assert payload.file_usage_ctx == "TestSuiteDummyString"


def test_get_context_payload_uses_first_arg_for_failed_locator(monkeypatch: Any) -> None:
    builtin_stub: DummyBuiltIn = patch_module_symbols(monkeypatch)
    dom_util: FakeDomUtils = FakeDomUtils("<DOM/>")
    kw: FakeKeyword = FakeKeyword(
        name="Type Text",
        args=["${first}", "${second}", "foo=bar"],
        message="fail"
    )

    data: FakeData = FakeData(file_usage_ctx="")

    payload: FakePromptPayload = RobotCtxRetriever.get_context_payload(
        data, kw, dom_util
    )

    assert payload.failed_locator == "LOC::${first}"
    assert builtin_stub.calls == ["${first}"]

