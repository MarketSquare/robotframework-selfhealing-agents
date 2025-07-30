import os

from RobotAid.utils.cfg import ClientSettings


def test_defaults_are_none() -> None:
    os.environ.pop("AZURE_API_KEY", None)
    os.environ.pop("AZURE_ENDPOINT", None)
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("BASE_URL", None)
    s = ClientSettings()
    assert s.azure_api_key is None
    assert s.azure_endpoint is None
    assert s.openai_api_key is None
    assert s.base_url is None


def test_loads_from_env(monkeypatch) -> None:
    monkeypatch.setenv("AZURE_API_KEY", "az_key")
    monkeypatch.setenv("AZURE_ENDPOINT", "https://example.azure.com")
    monkeypatch.setenv("OPENAI_API_KEY", "oa_key")
    monkeypatch.setenv("BASE_URL", "https://api.example.com")
    s = ClientSettings()
    assert s.azure_api_key == "az_key"
    assert s.azure_endpoint == "https://example.azure.com"
    assert s.openai_api_key == "oa_key"
    assert s.base_url == "https://api.example.com"


def test_override_env_with_init_arg(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "from_env")
    s = ClientSettings(openai_api_key="from_arg")
    assert s.openai_api_key == "from_arg"
    assert s.azure_api_key is None


def test_empty_string_env(monkeypatch) -> None:
    monkeypatch.setenv("BASE_URL", "")
    s = ClientSettings()
    assert s.base_url == ""
