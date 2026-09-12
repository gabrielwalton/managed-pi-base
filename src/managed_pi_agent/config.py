from __future__ import annotations

import os
import re
import socket
from dataclasses import dataclass
from pathlib import Path

SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _safe_id(value: str, name: str) -> str:
    value = value.strip().lower()
    if not SAFE_ID.fullmatch(value):
        raise ValueError(f"{name} must match {SAFE_ID.pattern}")
    return value


def _hardware_suffix() -> str:
    candidates = (
        Path("/proc/device-tree/serial-number"),
        Path("/etc/machine-id"),
    )
    for path in candidates:
        try:
            value = path.read_text(encoding="utf-8", errors="ignore").strip("\x00\n ")
        except OSError:
            continue
        safe = re.sub(r"[^a-zA-Z0-9]", "", value).lower()
        if safe:
            return safe[-8:]
    return re.sub(r"[^a-z0-9]", "", socket.gethostname().lower())[-8:] or "unknown"


def _device_id() -> str:
    configured = os.getenv("MANAGED_PI_DEVICE_ID", "").strip().lower()
    if configured and configured != "auto":
        return _safe_id(configured, "MANAGED_PI_DEVICE_ID")
    prefix = _safe_id(
        os.getenv("MANAGED_PI_DEVICE_ID_PREFIX", "managed-pi"),
        "MANAGED_PI_DEVICE_ID_PREFIX",
    )
    return _safe_id(f"{prefix}-{_hardware_suffix()}", "derived device id")


@dataclass(frozen=True)
class Config:
    device_id: str
    device_name: str
    mqtt_host: str
    mqtt_port: int
    mqtt_username: str | None
    mqtt_password: str | None
    mqtt_discovery_prefix: str
    repo_url: str
    repo_branch: str
    base_dir: Path
    service_name: str
    health_delay_seconds: float
    release_keep_count: int

    @property
    def topic_prefix(self) -> str:
        return f"managed-pi/{self.device_id}"


def load_config() -> Config:
    device_id = _device_id()
    branch = os.getenv("MANAGED_PI_REPO_BRANCH", "main").strip()
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", branch) or ".." in branch:
        raise ValueError("MANAGED_PI_REPO_BRANCH contains unsafe characters")

    port = int(os.getenv("MANAGED_PI_MQTT_PORT", "1883"))
    delay = float(os.getenv("MANAGED_PI_HEALTH_DELAY_SECONDS", "5"))
    keep = int(os.getenv("MANAGED_PI_RELEASE_KEEP_COUNT", "3"))
    if not 1 <= port <= 65535:
        raise ValueError("MANAGED_PI_MQTT_PORT is invalid")
    if not 0 <= delay <= 300:
        raise ValueError("MANAGED_PI_HEALTH_DELAY_SECONDS is invalid")
    if not 2 <= keep <= 20:
        raise ValueError("MANAGED_PI_RELEASE_KEEP_COUNT must be 2-20")

    return Config(
        device_id=device_id,
        device_name=os.getenv("MANAGED_PI_DEVICE_NAME", device_id).strip() or device_id,
        mqtt_host=_required("MANAGED_PI_MQTT_HOST"),
        mqtt_port=port,
        mqtt_username=os.getenv("MANAGED_PI_MQTT_USERNAME") or None,
        mqtt_password=os.getenv("MANAGED_PI_MQTT_PASSWORD") or None,
        mqtt_discovery_prefix=os.getenv(
            "MANAGED_PI_DISCOVERY_PREFIX", "homeassistant"
        ).strip("/"),
        repo_url=_required("MANAGED_PI_APP_REPO"),
        repo_branch=branch,
        base_dir=Path(os.getenv("MANAGED_PI_BASE_DIR", "/opt/managed-pi")),
        service_name="managed-pi-app.service",
        health_delay_seconds=delay,
        release_keep_count=keep,
    )
