import sys
import types
import pytest
import importlib
from bs4 import BeautifulSoup, Tag
from typing import Any, Callable, Dict, List, Tuple, Optional


MODULE_PATH: str = "SelfhealingAgents.self_healing_system.context_retrieving.library_dom_utils.selenium_dom_utils"


def _install_stub_logging_if_needed() -> None:
    try:
        import SelfhealingAgents
        return
    except Exception:
        pass
    pkg = types.ModuleType("SelfhealingAgents")
    pkg.__path__ = []
    utils = types.ModuleType("SelfhealingAgents.utils")
    utils.__path__ = []
    logging_mod = types.ModuleType("SelfhealingAgents.utils.logging")
    def log(func: Callable[..., Any]) -> Callable[..., Any]:
        return func
    logging_mod.log = log
    sys.modules["SelfhealingAgents"] = pkg
    sys.modules["SelfhealingAgents.utils"] = utils
    sys.modules["SelfhealingAgents.utils.logging"] = logging_mod


def _import_module_fresh() -> Any:
    if MODULE_PATH in sys.modules:
        del sys.modules[MODULE_PATH]
    return importlib.import_module(MODULE_PATH)


@pytest.fixture()
def mod_and_cls(monkeypatch: Any) -> Tuple[Any, Any]:
    _install_stub_logging_if_needed()
    mod = _import_module_fresh()
    return mod, getattr(mod, "SeleniumDomUtils")


class BuiltInStubNone:
    def get_library_instance(self, name: str) -> None:
        return None


class BuiltInStubWithLib:
    def __init__(self, lib: Any) -> None:
        self._lib: Any = lib
    def get_library_instance(self, name: str) -> Any:
        return self._lib


def _patch_built_in(monkeypatch: Any, mod: Any, lib: Any) -> None:
    monkeypatch.setattr(mod, "BuiltIn", lambda: BuiltInStubWithLib(lib), raising=True)


def _patch_built_in_none(monkeypatch: Any, mod: Any) -> None:
    monkeypatch.setattr(mod, "BuiltIn", lambda: BuiltInStubNone(), raising=True)


def test_is_locator_valid_returns_true_when_library_none(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, SeleniumDomUtils = mod_and_cls
    _patch_built_in_none(monkeypatch, mod)
    inst = SeleniumDomUtils()
    assert inst.is_locator_valid("id=x") is True


def test_is_locator_valid_calls_get_webelement(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, SeleniumDomUtils = mod_and_cls
    class Lib:
        def get_webelement(self, locator: str) -> str:
            return "ELEMENT"
    _patch_built_in(monkeypatch, mod, Lib())
    inst = SeleniumDomUtils()
    assert inst.is_locator_valid("id=x") is True


def test_is_locator_valid_handles_exception(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, SeleniumDomUtils = mod_and_cls
    class Lib:
        def get_webelement(self, locator: str) -> str:
            raise RuntimeError("boom")
    _patch_built_in(monkeypatch, mod, Lib())
    inst = SeleniumDomUtils()
    assert inst.is_locator_valid("id=x") is False


def test_is_locator_unique_when_one_element(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, SeleniumDomUtils = mod_and_cls
    class Lib:
        def get_webelements(self, locator: str) -> List[str]:
            return ["E1"]
    _patch_built_in(monkeypatch, mod, Lib())
    inst = SeleniumDomUtils()
    assert inst.is_locator_unique("css=#a") is True


def test_is_locator_unique_handles_exception(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, SeleniumDomUtils = mod_and_cls
    class Lib:
        def get_webelements(self, locator: str) -> List[str]:
            raise ValueError("nope")
    _patch_built_in(monkeypatch, mod, Lib())
    inst = SeleniumDomUtils()
    assert inst.is_locator_unique("css=#a") is False


def test_get_dom_tree_returns_not_available_when_no_library(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, SeleniumDomUtils = mod_and_cls
    _patch_built_in_none(monkeypatch, mod)
    inst = SeleniumDomUtils()
    assert inst.get_dom_tree() == "<html><body>SeleniumLibrary not available</body></html>"


def test_get_dom_tree_happy_path(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, SeleniumDomUtils = mod_and_cls
    class Lib:
        def get_source(self) -> str:
            return "<html><body><div id='x'>X</div></body></html>"
    class SDU:
        def get_simplified_dom_tree(self, src: str) -> str:
            return "<body><div id='x'>X</div></body>"
    _patch_built_in(monkeypatch, mod, Lib())
    monkeypatch.setattr(mod, "SoupDomUtils", SDU, raising=True)
    inst = SeleniumDomUtils()
    assert inst.get_dom_tree() == "<body><div id='x'>X</div></body>"


def test_get_dom_tree_handles_exception(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, SeleniumDomUtils = mod_and_cls
    class Lib:
        def get_source(self) -> str:
            raise RuntimeError("no source")
    _patch_built_in(monkeypatch, mod, Lib())
    inst = SeleniumDomUtils()
    out: str = inst.get_dom_tree()
    assert out.startswith("<html><body>Error retrieving DOM tree:")
    assert "no source" in out


def test_get_library_type(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, SeleniumDomUtils = mod_and_cls
    class Lib: ...
    _patch_built_in(monkeypatch, mod, Lib())
    inst = SeleniumDomUtils()
    assert inst.get_library_type() == "selenium"


def test_is_element_clickable_button(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, SeleniumDomUtils = mod_and_cls
    class Element:
        tag_name: str = "button"
    class Lib:
        def get_webelement(self, loc: str) -> Any:
            return Element()
        def execute_javascript(self, script: str, arg: str, elem: Any) -> Any:
            return None
    _patch_built_in(monkeypatch, mod, Lib())
    inst = SeleniumDomUtils()
    assert inst.is_element_clickable("id=btn") is True


def test_is_element_clickable_input_submit(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, SeleniumDomUtils = mod_and_cls
    class Element:
        tag_name: str = "input"
    class Lib:
        def get_webelement(self, loc: str) -> Any:
            return Element()
        def execute_javascript(self, script: str, arg: str, elem: Any) -> Any:
            if "arguments[0].type" in script:
                return "submit"
            if "getComputedStyle" in script:
                return ""
            return None
    _patch_built_in(monkeypatch, mod, Lib())
    inst = SeleniumDomUtils()
    assert inst.is_element_clickable("id=submit") is True


def test_is_element_clickable_pointer_style(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, SeleniumDomUtils = mod_and_cls
    class Element:
        tag_name: str = "div"
    class Lib:
        def get_webelement(self, loc: str) -> Any:
            return Element()
        def execute_javascript(self, script: str, arg: str, elem: Any) -> Any:
            if "getComputedStyle" in script:
                return "pointer"
            if "arguments[0].type" in script:
                return ""
            return None
    _patch_built_in(monkeypatch, mod, Lib())
    inst = SeleniumDomUtils()
    assert inst.is_element_clickable("id=div") is True


def test_is_element_clickable_handles_exception(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, SeleniumDomUtils = mod_and_cls
    class Lib:
        def get_webelement(self, loc: str) -> Any:
            raise RuntimeError("boom")
    _patch_built_in(monkeypatch, mod, Lib())
    inst = SeleniumDomUtils()
    assert inst.is_element_clickable("id=x") is False


def test_get_locator_proposals_input_text(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, SeleniumDomUtils = mod_and_cls
    _patch_built_in_none(monkeypatch, mod)
    html: str = """
    <body>
      <div>
        <input id="i1" />
        <textarea id="t1">hello</textarea>
        <div id="other">noop</div>
      </div>
    </body>
    """
    monkeypatch.setattr(
        getattr(mod, "SeleniumDomUtils"),
        "get_dom_tree",
        lambda self: html,
        raising=False,
    )
    class SDU:
        @staticmethod
        def is_leaf_or_lowest(tag: Tag) -> bool:
            return True
        @staticmethod
        def has_direct_text(tag: Tag) -> bool:
            return True
        @staticmethod
        def has_parent_dialog_without_open(tag: Tag) -> bool:
            return False
        @staticmethod
        def has_child_dialog_without_open(tag: Tag) -> bool:
            return False
        @staticmethod
        def is_headline(tag: Tag) -> bool:
            return False
        @staticmethod
        def is_div_in_li(tag: Tag) -> bool:
            return False
        @staticmethod
        def is_p(tag: Tag) -> bool:
            return False
    monkeypatch.setattr(mod, "SoupDomUtils", SDU, raising=True)
    monkeypatch.setattr(
        getattr(mod, "SeleniumDomUtils"),
        "_get_locator",
        lambda elem, soup: f"xpath://{elem.name}",
        raising=False,
    )
    inst = getattr(mod, "SeleniumDomUtils")()
    out: List[str] = inst.get_locator_proposals("bad", "Input Text")
    assert out == ["xpath://textarea", "xpath://input"] or out == ["xpath://input", "xpath://textarea"]


def test_get_locator_metadata_happy_path(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, SeleniumDomUtils = mod_and_cls
    class Elem:
        tag_name: str = "button"
        def get_attribute(self, name: str) -> Optional[str]:
            mapping = {"id": "idx", "class": "cls", "role": "btn", "placeholder": None, "href": None, "title": None}
            return mapping.get(name)
        def is_displayed(self) -> bool:
            return True
        def is_enabled(self) -> bool:
            return True
        def is_selected(self) -> bool:
            return False
    class Lib:
        def get_webelement(self, loc: str) -> Any:
            return Elem()
        def execute_javascript(self, script: str, arg: str, elem: Any) -> Any:
            if "arguments[0].tagName" in script:
                return "BUTTON"
            if "arguments[0].childElementCount" in script:
                return 3
            if "arguments[0].innerText" in script:
                return "Click me"
            if "arguments[0].type" in script:
                return "button"
            if "arguments[0].value" in script:
                return "val"
            if "arguments[0].name" in script:
                return "nm"
            if "parentElement.tagName" in script:
                return "DIV"
            if "getComputedStyle" in script:
                return ""
            return None
    _patch_built_in(monkeypatch, mod, Lib())
    inst = getattr(mod, "SeleniumDomUtils")()
    meta: List[Dict[str, Any]] = inst.get_locator_metadata("id=btn")
    assert len(meta) == 1
    m = meta[0]
    assert m["tagName"] == "BUTTON"
    assert m["childElementCount"] == "3"
    assert m["innerText"] == "Click me"
    assert m["type"] == "button"
    assert m["value"] == "val"
    assert m["name"] == "nm"
    assert m["id"] == "idx"
    assert m["class"] == "cls"
    assert m["role"] == "btn"
    assert m["is_displayed"] is True
    assert m["is_enabled"] is True
    assert m["is_selected"] is False
    assert m["clickable"] is True


def test_get_locator_metadata_clickable_via_pointer(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, SeleniumDomUtils = mod_and_cls
    class Elem:
        tag_name: str = "div"
        def get_attribute(self, name: str) -> Optional[str]:
            return None
        def is_displayed(self) -> bool:
            return False
        def is_enabled(self) -> bool:
            return False
        def is_selected(self) -> bool:
            return False
    class Lib:
        def get_webelement(self, loc: str) -> Any:
            return Elem()
        def execute_javascript(self, script: str, arg: str, elem: Any) -> Any:
            if "arguments[0].tagName" in script:
                return "DIV"
            if "getComputedStyle" in script:
                return "pointer"
            return None
    _patch_built_in(monkeypatch, mod, Lib())
    inst = getattr(mod, "SeleniumDomUtils")()
    meta: List[Dict[str, Any]] = inst.get_locator_metadata("id=x")
    assert len(meta) == 1
    assert meta[0]["clickable"] is True


def test__get_locator_uses_soup(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, SeleniumDomUtils = mod_and_cls
    class SDU:
        @staticmethod
        def generate_unique_xpath_selector(elem: Tag, soup: BeautifulSoup) -> Optional[str]:
            return "//p[@id='p1']"
    monkeypatch.setattr(mod, "SoupDomUtils", SDU, raising=True)
    soup: BeautifulSoup = BeautifulSoup("<body><p id='p1'>hi</p></body>", "html.parser")
    elem: Tag = soup.select_one("#p1")
    out: Optional[str] = getattr(mod, "SeleniumDomUtils")._get_locator(elem, soup)
    assert out == "xpath://p[@id='p1']"


def test__get_locator_returns_none_when_no_selector(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, SeleniumDomUtils = mod_and_cls
    class SDU:
        @staticmethod
        def generate_unique_xpath_selector(elem: Tag, soup: BeautifulSoup) -> Optional[str]:
            return None
    monkeypatch.setattr(mod, "SoupDomUtils", SDU, raising=True)
    soup: BeautifulSoup = BeautifulSoup("<body><div id='x'></div></body>", "html.parser")
    elem: Tag = soup.select_one("#x")
    out: Optional[str] = getattr(mod, "SeleniumDomUtils")._get_locator(elem, soup)
    assert out is None
