import yaml
import pytest
from pathlib import Path
from pydantic import ValidationError

from RobotAid.utils.app_settings import SystemSettings, OrchestratorAgentSettings, LocatorAgentSettings, AppSettings


def test_system_settings_valid() -> None:
    s = SystemSettings(enabled=True, max_retries=5)
    assert s.enabled is True
    assert s.max_retries == 5

def test_system_settings_default_max_retries() -> None:
    s = SystemSettings(enabled=False)
    assert s.enabled is False
    assert s.max_retries == 3

def test_system_settings_negative_retries() -> None:
    with pytest.raises(ValidationError):
        SystemSettings(enabled=True, max_retries=-1)

def test_system_settings_extra_field() -> None:
    with pytest.raises(ValidationError):
        SystemSettings(enabled=True, max_retries=1, foo='bar')  # type: ignore

def test_orchestrator_agent_defaults() -> None:
    o = OrchestratorAgentSettings()
    assert o.provider == "openai"
    assert o.model == "gpt-4o"

def test_orchestrator_agent_override() -> None:
    o = OrchestratorAgentSettings(provider="anthropic", model="claude")
    assert o.provider == "anthropic"
    assert o.model == "claude"

def test_orchestrator_agent_extra_field() -> None:
    with pytest.raises(ValidationError):
        OrchestratorAgentSettings(provider="openai", model="gpt-4o", extra='x')  # type: ignore

def test_locator_agent_defaults() -> None:
    l = LocatorAgentSettings()
    assert l.provider == "openai"
    assert l.model == "gpt-4o"

def test_locator_agent_override() -> None:
    l = LocatorAgentSettings(provider="azure", model="gpt-35-turbo")
    assert l.provider == "azure"
    assert l.model == "gpt-35-turbo"

def test_locator_agent_extra_field() -> None:
    with pytest.raises(ValidationError):
        LocatorAgentSettings(provider="openai", model="gpt-4o", foo='bar')  # type: ignore


def test_app_settings_from_yaml_valid(tmp_path: Path) -> None:
    cfg = {
        "system": {"enabled": True, "max_retries": 2},
        "orchestrator_agent": {},
        "locator_agent": {},
    }
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.dump(cfg))
    app = AppSettings.from_yaml(str(p))
    assert isinstance(app.system, SystemSettings)
    assert app.system.enabled is True
    assert app.system.max_retries == 2
    assert isinstance(app.orchestrator_agent, OrchestratorAgentSettings)
    assert isinstance(app.locator_agent, LocatorAgentSettings)

def test_app_settings_from_yaml_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        AppSettings.from_yaml("does_not_exist.yaml")

def test_app_settings_from_yaml_invalid_root(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.dump([1, 2, 3]))
    with pytest.raises(ValueError) as exc:
        AppSettings.from_yaml(str(p))
    assert "Expected top-level dict in config, got list" in str(exc.value)

def test_app_settings_from_yaml_missing_required_field(tmp_path: Path) -> None:
    cfg = {
        "system": {"max_retries": 2},
        "orchestrator_agent": {},
        "locator_agent": {},
    }
    p = tmp_path / "missing_field.yaml"
    p.write_text(yaml.dump(cfg))
    with pytest.raises(ValueError) as exc:
        AppSettings.from_yaml(str(p))
    msg = str(exc.value)
    assert "Config validation error" in msg
    assert "system.enabled" in msg
