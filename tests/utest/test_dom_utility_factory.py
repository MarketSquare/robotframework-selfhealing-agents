import pytest
import importlib
from typing import Any, Dict, Mapping, Type


MODULE_PATH: str = "RobotAid.self_healing_system.context_retrieving.dom_utility_factory"
mod = importlib.import_module(MODULE_PATH)
DomUtilityFactory = getattr(mod, "DomUtilityFactory")


class DummyBaseDomUtils:
    pass


class DummyBrowserDomUtils(DummyBaseDomUtils):
    def __init__(self) -> None:
        self.kind: str = "browser"


class DummySeleniumDomUtils(DummyBaseDomUtils):
    def __init__(self) -> None:
        self.kind: str = "selenium"


class DummyAppiumDomUtils(DummyBaseDomUtils):
    def __init__(self) -> None:
        self.kind: str = "appium"


def _patch_mapping(monkeypatch: Any) -> Mapping[str, Type[DummyBaseDomUtils]]:
    mapping: Dict[str, Type[DummyBaseDomUtils]] = {
        "browser": DummyBrowserDomUtils,
        "selenium": DummySeleniumDomUtils,
        "appium": DummyAppiumDomUtils,
    }
    monkeypatch.setattr(mod, "_DOM_UTILITY_TYPE", mapping, raising=True)
    return mapping


@pytest.mark.parametrize(
    ("agent_type", "expected_cls"),
    [
        ("browser", DummyBrowserDomUtils),
        ("selenium", DummySeleniumDomUtils),
        ("appium", DummyAppiumDomUtils),
    ],
)
def test_create_dom_utility_supported_types(monkeypatch: Any, agent_type: str, expected_cls: Type[DummyBaseDomUtils]) -> None:
    _patch_mapping(monkeypatch)
    instance: DummyBaseDomUtils = DomUtilityFactory.create_dom_utility(agent_type)
    assert isinstance(instance, expected_cls)
    assert getattr(instance, "kind") == agent_type


def test_create_dom_utility_returns_new_instance_each_call(monkeypatch: Any) -> None:
    _patch_mapping(monkeypatch)
    a: DummyBaseDomUtils = DomUtilityFactory.create_dom_utility("browser")
    b: DummyBaseDomUtils = DomUtilityFactory.create_dom_utility("browser")
    assert isinstance(a, DummyBrowserDomUtils)
    assert isinstance(b, DummyBrowserDomUtils)
    assert a is not b


def test_create_dom_utility_unsupported_type_raises(monkeypatch: Any) -> None:
    _patch_mapping(monkeypatch)
    with pytest.raises(ValueError) as exc:
        DomUtilityFactory.create_dom_utility("unknown")
    msg: str = str(exc.value)
    assert "Unsupported DOM utility type" in msg
    assert "None" in msg
