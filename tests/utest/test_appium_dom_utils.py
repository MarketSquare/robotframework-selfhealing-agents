import sys
import types
import importlib
import pytest
from typing import Any, Tuple, List


MODULE_PATH: str = "SelfhealingAgents.self_healing_system.context_retrieving.library_dom_utils.appium_dom_utils"


def _install_stub_logging_if_needed() -> None:
    try:
        import SelfhealingAgents  # noqa: F401
        return
    except Exception:
        pass
    pkg = types.ModuleType("SelfhealingAgents")
    pkg.__path__ = []
    utils = types.ModuleType("SelfhealingAgents.utils")
    utils.__path__ = []
    logging_mod = types.ModuleType("SelfhealingAgents.utils.logging")

    def log(func):
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
def mod_and_cls(monkeypatch: pytest.MonkeyPatch) -> Tuple[Any, Any]:
    _install_stub_logging_if_needed()
    mod = _import_module_fresh()
    return mod, getattr(mod, "AppiumDomUtils")


class BuiltInStubNone:
    def get_library_instance(self, name: str) -> None:  # pragma: no cover
        return None


class BuiltInStubWithLib:
    def __init__(self, lib: Any) -> None:
        self._lib = lib

    def get_library_instance(self, name: str) -> Any:  # pragma: no cover
        return self._lib


def _patch_built_in(monkeypatch: pytest.MonkeyPatch, mod: Any, lib: Any) -> None:
    monkeypatch.setattr(mod, "BuiltIn", lambda: BuiltInStubWithLib(lib), raising=True)


def _patch_built_in_none(monkeypatch: pytest.MonkeyPatch, mod: Any) -> None:
    monkeypatch.setattr(mod, "BuiltIn", lambda: BuiltInStubNone(), raising=True)


def test_is_locator_valid_with_none_lib(monkeypatch: pytest.MonkeyPatch, mod_and_cls) -> None:
    mod, AppiumDomUtils = mod_and_cls
    _patch_built_in_none(monkeypatch, mod)
    inst = AppiumDomUtils()
    assert inst.is_locator_valid("//x") is True


def test_is_locator_valid_counts_elements(monkeypatch: pytest.MonkeyPatch, mod_and_cls) -> None:
    mod, AppiumDomUtils = mod_and_cls

    class Lib:
        def get_webelements(self, locator: str) -> List[str]:
            return ["e1"]

    _patch_built_in(monkeypatch, mod, Lib())
    inst = AppiumDomUtils()
    assert inst.is_locator_valid("//x") is True
    assert inst.is_locator_unique("//x") is True


def test_get_dom_tree_uses_get_source(monkeypatch: pytest.MonkeyPatch, mod_and_cls) -> None:
    mod, AppiumDomUtils = mod_and_cls

    class Lib:
        def get_source(self) -> str:
            return "<hierarchy><node text='Hello' resource-id='app:id/x'/></hierarchy>"

    _patch_built_in(monkeypatch, mod, Lib())
    inst = AppiumDomUtils()
    out = inst.get_dom_tree()
    assert out.startswith("<hierarchy>") and "Hello" in out


def test_get_dom_tree_handles_session_error(monkeypatch: pytest.MonkeyPatch, mod_and_cls) -> None:
    mod, AppiumDomUtils = mod_and_cls

    class Driver:
        @property
        def page_source(self) -> str:  # pragma: no cover - simple property access
            return "<hierarchy><node text='Fallback'/></hierarchy>"

    class Lib:
        def __init__(self) -> None:
            self._current_application = Driver()

        def get_source(self) -> str:
            return (
                '{"value":{"message":"Unable to find session with requested ID: 123"},'
                '"sessionId":"123","status":13}'
            )

    _patch_built_in(monkeypatch, mod, Lib())
    inst = AppiumDomUtils()
    out = inst.get_dom_tree()
    assert out.startswith("<hierarchy>") and "Fallback" in out


def test_get_dom_tree_returns_error_message_when_no_fallback(monkeypatch: pytest.MonkeyPatch, mod_and_cls) -> None:
    mod, AppiumDomUtils = mod_and_cls

    class Lib:
        def get_source(self) -> str:
            return '{"value":{"message":"Unable to find session"}}'

    _patch_built_in(monkeypatch, mod, Lib())
    inst = AppiumDomUtils()
    out = inst.get_dom_tree()
    assert "Error retrieving DOM tree" in out
    assert "Unable to find session" in out


def test_get_locator_proposals_include_failed_locator_hints(monkeypatch, mod_and_cls) -> None:
    mod, AppiumDomUtils = mod_and_cls

    class Lib:
        def get_source(self) -> str:
            return "<hierarchy/>"

    _patch_built_in(monkeypatch, mod, Lib())
    inst = AppiumDomUtils()
    proposals = inst.get_locator_proposals(
        '//android.widget.TextView[@text="Sauce Labs Onesie"]',
        "Click Element",
    )
    assert any("Sauce Labs Onesie" in proposal for proposal in proposals)


def test_get_library_type(monkeypatch: pytest.MonkeyPatch, mod_and_cls) -> None:
    mod, AppiumDomUtils = mod_and_cls
    class Lib: ...
    _patch_built_in(monkeypatch, mod, Lib())
    inst = AppiumDomUtils()
    assert inst.get_library_type() == "appium"


def test_is_element_clickable_heuristics(monkeypatch: pytest.MonkeyPatch, mod_and_cls) -> None:
    mod, AppiumDomUtils = mod_and_cls

    class El:
        def __init__(self) -> None:
            self._attrs = {
                "displayed": "true",
                "enabled": "true",
                "clickable": "true",
                "class": "android.widget.Button",
            }

        def get_attribute(self, name: str) -> str:
            return self._attrs.get(name, "")

        @property
        def tag_name(self) -> str:
            return "android.widget.Button"

    class Lib:
        def get_webelements(self, locator: str) -> List[El]:
            return [El()]

    _patch_built_in(monkeypatch, mod, Lib())
    inst = AppiumDomUtils()
    assert inst.is_element_clickable("//button") is True


def test_get_locator_proposals_from_source(monkeypatch: pytest.MonkeyPatch, mod_and_cls) -> None:
    mod, AppiumDomUtils = mod_and_cls

    xml = (
        "<hierarchy>"
        "  <android.widget.EditText resource-id='app:id/username' text='user'/>"
        "  <android.widget.Button content-desc='Submit' text='LOGIN'/>"
        "</hierarchy>"
    )

    class Lib:
        def get_source(self) -> str:
            return xml

        def get_webelements(self, locator: str) -> List[str]:
            # Not strictly used here, but keep interface available
            return []

    _patch_built_in(monkeypatch, mod, Lib())
    inst = AppiumDomUtils()
    props_input = inst.get_locator_proposals("//bad", "Input Text")
    assert any("@resource-id='app:id/username'" in p for p in props_input)
    props_click = inst.get_locator_proposals("//bad", "Click Element")
    assert any("@content-desc='Submit'" in p or "LOGIN" in p for p in props_click)
