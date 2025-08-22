import sys
import types
import pytest
import importlib
from bs4 import BeautifulSoup, Tag
from typing import Any, Callable, Dict, List, Tuple, Optional


MODULE_PATH: str = "RobotAid.self_healing_system.context_retrieving.library_dom_utils.browser_dom_utils"


def _install_stub_logging_if_needed() -> None:
    try:
        import RobotAid.utils.logging
        return
    except Exception:
        pass
    pkg = types.ModuleType("RobotAid")
    pkg.__path__ = []
    utils = types.ModuleType("RobotAid.utils")
    utils.__path__ = []
    logging_mod = types.ModuleType("RobotAid.utils.logging")
    def log(func: Callable[..., Any]) -> Callable[..., Any]:
        return func
    logging_mod.log = log
    sys.modules["RobotAid"] = pkg
    sys.modules["RobotAid.utils"] = utils
    sys.modules["RobotAid.utils.logging"] = logging_mod


def _import_module_fresh() -> Any:
    if MODULE_PATH in sys.modules:
        del sys.modules[MODULE_PATH]
    return importlib.import_module(MODULE_PATH)


@pytest.fixture()
def mod_and_cls(monkeypatch: Any) -> Tuple[Any, Any]:
    _install_stub_logging_if_needed()
    mod = _import_module_fresh()
    return mod, getattr(mod, "BrowserDomUtils")


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
    mod, BrowserDomUtils = mod_and_cls
    _patch_built_in_none(monkeypatch, mod)
    inst = BrowserDomUtils()
    assert inst.is_locator_valid("css=div") is True


def test_is_locator_valid_uses_get_elements(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, BrowserDomUtils = mod_and_cls
    class Lib:
        def get_elements(self, locator: str) -> List[str]:
            return ["e1", "e2"]
    _patch_built_in(monkeypatch, mod, Lib())
    inst = BrowserDomUtils()
    assert inst.is_locator_valid("css=div") is True


def test_is_locator_valid_handles_exception(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, BrowserDomUtils = mod_and_cls
    class Lib:
        def get_elements(self, locator: str) -> List[str]:
            raise RuntimeError("boom")
    _patch_built_in(monkeypatch, mod, Lib())
    inst = BrowserDomUtils()
    assert inst.is_locator_valid("css=div") is False


def test_is_locator_unique_true_when_count_one(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, BrowserDomUtils = mod_and_cls
    class Lib:
        def get_element_count(self, locator: str) -> int:
            return 1
    _patch_built_in(monkeypatch, mod, Lib())
    inst = BrowserDomUtils()
    assert inst.is_locator_unique("css=#x") is True


def test_is_locator_unique_handles_exception(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, BrowserDomUtils = mod_and_cls
    class Lib:
        def get_element_count(self, locator: str) -> int:
            raise ValueError("nope")
    _patch_built_in(monkeypatch, mod, Lib())
    inst = BrowserDomUtils()
    assert inst.is_locator_unique("css=#x") is False


def test_get_dom_tree_shadow_dom_path(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, BrowserDomUtils = mod_and_cls
    html_shadow: str = "<html><body><div id='a'>A</div></body></html>"
    class Lib:
        def evaluate_javascript(self, ctx: Any, script: str) -> Any:
            if "shadowRoot" in script and "some(" in script:
                return True
            return html_shadow
        def get_page_source(self) -> str:
            raise AssertionError("should not be called")
    class SDU:
        def get_simplified_dom_tree(self, src: str) -> str:
            return "<body><div id='a'>A</div></body>"
    _patch_built_in(monkeypatch, mod, Lib())
    monkeypatch.setattr(mod, "SoupDomUtils", SDU, raising=True)
    inst = BrowserDomUtils()
    out: str = inst.get_dom_tree()
    assert out == "<body><div id='a'>A</div></body>"


def test_get_dom_tree_plain_source_path(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, BrowserDomUtils = mod_and_cls
    html_plain: str = "<html><body><div id='b'>B</div></body></html>"
    class Lib:
        def evaluate_javascript(self, ctx: Any, script: str) -> Any:
            if "shadowRoot" in script and "some(" in script:
                return False
            raise AssertionError("should not request full shadow html")
        def get_page_source(self) -> str:
            return html_plain
    class SDU:
        def get_simplified_dom_tree(self, src: str) -> str:
            return "<body><div id='b'>B</div></body>"
    _patch_built_in(monkeypatch, mod, Lib())
    monkeypatch.setattr(mod, "SoupDomUtils", SDU, raising=True)
    inst = BrowserDomUtils()
    out: str = inst.get_dom_tree()
    assert out == "<body><div id='b'>B</div></body>"


def test_get_dom_tree_double_fallback_error(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, BrowserDomUtils = mod_and_cls
    class Lib:
        def evaluate_javascript(self, ctx: Any, script: str) -> Any:
            raise RuntimeError("first path fails")
        def get_page_source(self) -> str:
            raise RuntimeError("second path fails")
    class SDU:
        def get_simplified_dom_tree(self, src: str) -> str:
            return "IGNORED"
    _patch_built_in(monkeypatch, mod, Lib())
    monkeypatch.setattr(mod, "SoupDomUtils", SDU, raising=True)
    inst = BrowserDomUtils()
    out: str = inst.get_dom_tree()
    assert out == "<html><body>Unable to retrieve DOM tree</body></html>"


def test_get_library_type(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, BrowserDomUtils = mod_and_cls
    class Lib: ...
    _patch_built_in(monkeypatch, mod, Lib())
    inst = BrowserDomUtils()
    assert inst.get_library_type() == "browser"



def test_is_element_clickable_for_button(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, BrowserDomUtils = mod_and_cls
    class Lib:
        def get_element(self, locator: str) -> str:
            return "E"
        def get_property(self, element: str, prop: str) -> str:
            return "BUTTON"
        def evaluate_javascript(self, locator: str, script: str) -> str:
            return ""
        def get_style(self, locator: str, name: str) -> str:
            return ""
    _patch_built_in(monkeypatch, mod, Lib())
    inst = BrowserDomUtils()
    assert inst.is_element_clickable("css=#btn") is True


def test_is_element_clickable_input_submit(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, BrowserDomUtils = mod_and_cls
    class Lib:
        def get_element(self, locator: str) -> str:
            return "E"
        def get_property(self, element: str, prop: str) -> str:
            return "input"
        def evaluate_javascript(self, locator: str, script: str) -> str:
            return "submit"
        def get_style(self, locator: str, name: str) -> str:
            return ""
    _patch_built_in(monkeypatch, mod, Lib())
    inst = BrowserDomUtils()
    assert inst.is_element_clickable("css=#submit") is True


def test_is_element_clickable_pointer_style(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, BrowserDomUtils = mod_and_cls
    class Lib:
        def get_element(self, locator: str) -> str:
            return "E"
        def get_property(self, element: str, prop: str) -> str:
            return "div"
        def evaluate_javascript(self, locator: str, script: str) -> str:
            return ""
        def get_style(self, locator: str, name: str) -> str:
            return "pointer"
    _patch_built_in(monkeypatch, mod, Lib())
    inst = BrowserDomUtils()
    assert inst.is_element_clickable("css=#anything") is True


def test_is_element_clickable_handles_exception(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, BrowserDomUtils = mod_and_cls
    class Lib:
        def get_element(self, locator: str) -> str:
            raise RuntimeError("boom")
    _patch_built_in(monkeypatch, mod, Lib())
    inst = BrowserDomUtils()
    assert inst.is_element_clickable("css=#x") is False


def test__get_locator_uses_soupdomutils_static(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, BrowserDomUtils = mod_and_cls
    class SDU:
        @staticmethod
        def generate_unique_css_selector(elem: Tag, soup: BeautifulSoup) -> Optional[str]:
            return "p#p1"
    monkeypatch.setattr(mod, "SoupDomUtils", SDU, raising=True)
    html: str = "<body><p id='p1'>hi</p></body>"
    soup: BeautifulSoup = BeautifulSoup(html, "html.parser")
    elem: Tag = soup.select_one("#p1")
    out: Optional[str] = BrowserDomUtils._get_locator(elem, soup)
    assert out == "css=p#p1"


def test__get_locator_returns_none(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, BrowserDomUtils = mod_and_cls
    class SDU:
        @staticmethod
        def generate_unique_css_selector(elem: Tag, soup: BeautifulSoup) -> Optional[str]:
            return None
    monkeypatch.setattr(mod, "SoupDomUtils", SDU, raising=True)
    soup: BeautifulSoup = BeautifulSoup("<body><div id='x'></div></body>", "html.parser")
    elem: Tag = soup.select_one("#x")
    out: Optional[str] = BrowserDomUtils._get_locator(elem, soup)
    assert out is None


def test_get_locator_proposals_fill_text(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, BrowserDomUtils = mod_and_cls
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
        getattr(mod, "BrowserDomUtils"),
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
        getattr(mod, "BrowserDomUtils"),
        "_get_locator",
        lambda elem, soup: f"css={elem.name}",
        raising=False,
    )
    inst = getattr(mod, "BrowserDomUtils")()
    out: List[str] = inst.get_locator_proposals("css=#bad", "Fill Text")
    assert out == ["css=textarea", "css=input"] or out == ["css=input", "css=textarea"]


def test_get_locator_metadata_happy_path(monkeypatch: Any, mod_and_cls: Tuple[Any, Any]) -> None:
    mod, BrowserDomUtils = mod_and_cls
    class Lib:
        def get_elements(self, locator: str) -> List[str]:
            return ["E1", "E2"]
        def evaluate_javascript(self, element: str, script: str) -> Any:
            if ".tagName" in script:
                return "DIV"
            if ".childElementCount" in script:
                return 2
            if ".innerText" in script:
                return "hello"
            if ".type" in script:
                return "button"
            if ".value" in script:
                return "val"
            if ".name" in script:
                return "nm"
            if "parentElement.tagName" in script:
                return "BODY"
            return None
        def get_attribute_names(self, element: str) -> List[str]:
            return ["id", "class", "role"]
        def get_attribute(self, element: str, name: str) -> Optional[str]:
            data = {"id": "idx", "class": "cls", "role": "btn"}
            return data.get(name)
        def get_element_states(self, element: str) -> List[str]:
            return ["visible", "enabled"]
    _patch_built_in(monkeypatch, mod, Lib())
    inst = getattr(mod, "BrowserDomUtils")()
    meta: List[Dict[str, Any]] = inst.get_locator_metadata("css=#x")
    assert len(meta) == 2
    for m in meta:
        assert m["tagName"] == "DIV"
        assert m["childElementCount"] == "2"
        assert m["innerText"] == "hello"
        assert m["type"] == "button"
        assert m["value"] == "val"
        assert m["name"] == "nm"
        assert m["id"] == "idx"
        assert m["class"] == "cls"
        assert m["role"] == "btn"
        assert m["is_visible"] is True
        assert m["is_enabled"] is True
        assert m["is_checked"] is False
