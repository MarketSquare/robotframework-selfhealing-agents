import sys
import types
import importlib
import pytest
from typing import Any
from unittest.mock import MagicMock


AGENT_FACTORY_PATH = "SelfhealingAgents.self_healing_system.agents.locator_agent.locator_agent_factory"
APPIUM_AGENT_PATH = "SelfhealingAgents.self_healing_system.agents.locator_agent.appium_locator_agent"
PROMPTS_PATH = "SelfhealingAgents.self_healing_system.agents.prompts.locator.prompts_locator"


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


def _import_fresh(path: str) -> Any:
    if path in sys.modules:
        del sys.modules[path]
    return importlib.import_module(path)


def test_locator_agent_factory_appium_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_stub_logging_if_needed()
    appium_mod = _import_fresh(APPIUM_AGENT_PATH)
    factory_mod = _import_fresh(AGENT_FACTORY_PATH)

    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.agents.locator_agent.base_locator_agent.get_client_model",
        lambda provider, model, cfg: MagicMock(name=f"FakeModel[{provider}:{model}]")
    )
    monkeypatch.setattr(
        "SelfhealingAgents.self_healing_system.agents.locator_agent.base_locator_agent.BaseLocatorAgent.__init__",
        lambda self, cfg, dom_utility: None,
    )

    DummyCfg = type(
        "DummyCfg",
        (),
        {
            "request_limit": 1,
            "total_tokens_limit": 1,
            "use_llm_for_locator_generation": False,
            "locator_agent_provider": "openai",
            "locator_agent_model": "gpt-4o-mini",
        },
    )
    DummyDom = type("DummyDom", (), {"get_library_type": lambda self: "appium"})

    inst = factory_mod.LocatorAgentFactory.create_agent(
        "appium", cfg=DummyCfg(), dom_utility=DummyDom()
    )
    assert isinstance(inst, appium_mod.AppiumLocatorAgent)


def test_prompts_system_msg_appium() -> None:
    _install_stub_logging_if_needed()
    prompts_mod = _import_fresh(PROMPTS_PATH)
    # Create a tiny DomUtils stub that identifies as appium
    class DU:
        def get_library_type(self) -> str:
            return "appium"

    msg = prompts_mod.PromptsLocatorGenerationAgent.get_system_msg(DU())
    assert isinstance(msg, str)
    assert "APPIUM" in msg.upper()
    assert "XPATH" in msg.upper() or "RESOURCE-ID" in msg.lower()


def test_appium_error_detection_matches_appiumlibrary_message() -> None:
    _install_stub_logging_if_needed()
    appium_mod = _import_fresh(APPIUM_AGENT_PATH)

    err = "ValueError: Element locator '//foo' did not match any elements."
    assert appium_mod.AppiumLocatorAgent.is_failed_locator_error(err) is True
