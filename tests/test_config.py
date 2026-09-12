import pytest
from managed_pi_agent.config import load_config


def base_env(monkeypatch):
    monkeypatch.setenv("MANAGED_PI_MQTT_HOST", "mqtt.local")
    monkeypatch.setenv("MANAGED_PI_APP_REPO", "https://example.invalid/app.git")


def test_load_config(monkeypatch):
    base_env(monkeypatch)
    monkeypatch.setenv("MANAGED_PI_DEVICE_ID", "photo-viewer-1")
    config = load_config()
    assert config.device_id == "photo-viewer-1"
    assert config.topic_prefix == "managed-pi/photo-viewer-1"
    assert config.repo_branch == "main"


def test_rejects_unsafe_device_id(monkeypatch):
    base_env(monkeypatch)
    monkeypatch.setenv("MANAGED_PI_DEVICE_ID", "../../bad")
    with pytest.raises(ValueError):
        load_config()


def test_rejects_unsafe_branch(monkeypatch):
    base_env(monkeypatch)
    monkeypatch.setenv("MANAGED_PI_REPO_BRANCH", "../main")
    with pytest.raises(ValueError):
        load_config()


def test_auto_device_id_uses_prefix(monkeypatch):
    base_env(monkeypatch)
    monkeypatch.setenv("MANAGED_PI_DEVICE_ID", "auto")
    monkeypatch.setenv("MANAGED_PI_DEVICE_ID_PREFIX", "viewer")
    config = load_config()
    assert config.device_id.startswith("viewer-")
