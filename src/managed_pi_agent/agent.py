from __future__ import annotations

import json
import logging
import socket
import subprocess
import threading
import uuid
from datetime import UTC, datetime

import paho.mqtt.client as mqtt

from . import __version__
from .config import Config, load_config
from .deploy import Deployer, DeploymentError, DeploymentRolledBack

LOG = logging.getLogger("managed-pi-agent")


def now() -> str:
    return datetime.now(UTC).isoformat()


class Agent:
    def __init__(self, config: Config):
        self.config = config
        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"managed-pi-{config.device_id}",
        )
        if config.mqtt_username:
            self.client.username_pw_set(config.mqtt_username, config.mqtt_password)
        self.client.enable_logger(LOG)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.will_set(
            f"{config.topic_prefix}/availability", "offline", qos=1, retain=True
        )
        self.deployer = Deployer(config, self.publish_status)
        self.worker_lock = threading.Lock()

    def publish_json(self, topic: str, payload: dict, retain: bool = True) -> None:
        self.client.publish(
            topic, json.dumps(payload, separators=(",", ":")), qos=1, retain=retain
        )

    def publish_status(
        self, state: str, message: str, extra: dict | None = None
    ) -> None:
        payload = {
            "state": state,
            "message": message,
            "time": now(),
            "host": socket.gethostname(),
            "device_id": self.config.device_id,
            "agent_version": __version__,
            **self.deployer.versions(),
            **(extra or {}),
        }
        self.publish_json(f"{self.config.topic_prefix}/status", payload)
        if payload.get("installed_version"):
            self.client.publish(
                f"{self.config.topic_prefix}/version",
                payload["installed_version"],
                qos=1,
                retain=True,
            )

    def discovery(self) -> None:
        prefix = self.config.mqtt_discovery_prefix
        node = self.config.device_id
        base = self.config.topic_prefix
        device = {
            "identifiers": [f"managed-pi-{node}"],
            "name": self.config.device_name,
            "manufacturer": "Managed Pi",
            "model": "GitHub-deployed Raspberry Pi",
            "sw_version": __version__,
        }
        availability = [{"topic": f"{base}/availability"}]
        components = {
            "update": (
                "button",
                {
                    "name": "Update application",
                    "command_topic": f"{base}/command",
                    "payload_press": "update",
                    "icon": "mdi:update",
                },
            ),
            "check": (
                "button",
                {
                    "name": "Check for update",
                    "command_topic": f"{base}/command",
                    "payload_press": "check",
                    "icon": "mdi:cloud-search",
                },
            ),
            "rollback": (
                "button",
                {
                    "name": "Roll back application",
                    "command_topic": f"{base}/command",
                    "payload_press": "rollback",
                    "icon": "mdi:backup-restore",
                },
            ),
            "restart": (
                "button",
                {
                    "name": "Restart application",
                    "command_topic": f"{base}/command",
                    "payload_press": "restart",
                    "icon": "mdi:restart",
                },
            ),
            "status": (
                "sensor",
                {
                    "name": "Update status",
                    "state_topic": f"{base}/status",
                    "value_template": "{{ value_json.state }}",
                    "json_attributes_topic": f"{base}/status",
                    "icon": "mdi:progress-check",
                },
            ),
            "version": (
                "sensor",
                {
                    "name": "Installed version",
                    "state_topic": f"{base}/version",
                    "icon": "mdi:source-commit",
                },
            ),
        }
        for key, (domain, body) in components.items():
            payload = {
                **body,
                "unique_id": f"managed_pi_{node}_{key}",
                "device": device,
                "availability": availability,
            }
            self.publish_json(
                f"{prefix}/{domain}/managed_pi_{node}_{key}/config", payload
            )

    def on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        LOG.info("Connected to MQTT: %s", reason_code)
        client.subscribe(f"{self.config.topic_prefix}/command", qos=1)
        client.publish(
            f"{self.config.topic_prefix}/availability", "online", qos=1, retain=True
        )
        self.discovery()
        self.publish_status("ready", "Managed Pi agent is ready")

    def on_disconnect(
        self, client, userdata, disconnect_flags, reason_code, properties=None
    ) -> None:
        LOG.warning("Disconnected from MQTT: %s", reason_code)

    def on_message(self, client, userdata, message) -> None:
        if message.retain:
            LOG.warning("Ignoring retained command")
            return
        raw = message.payload.decode("utf-8", errors="replace").strip()
        request_id = uuid.uuid4().hex
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                command = str(parsed.get("command", "")).lower()
                request_id = str(parsed.get("request_id") or request_id)[:64]
            else:
                command = str(parsed).lower()
        except json.JSONDecodeError:
            command = raw.lower()
        if command not in {"check", "update", "rollback", "restart", "status"}:
            self.publish_status(
                "command_rejected", "Unknown command", {"request_id": request_id}
            )
            return
        if not self.worker_lock.acquire(blocking=False):
            self.publish_status(
                "busy", "Another command is already running", {"request_id": request_id}
            )
            return
        threading.Thread(
            target=self._run_command, args=(command, request_id), daemon=True
        ).start()

    def _run_command(self, command: str, request_id: str) -> None:
        try:
            self.publish_status(
                "working", f"Running {command}", {"request_id": request_id}
            )
            if command == "check":
                result = self.deployer.check()
            elif command == "update":
                result = self.deployer.update()
            elif command == "rollback":
                result = self.deployer.rollback()
            elif command == "restart":
                result = self.deployer.restart()
            else:
                result = {"state": "ready", **self.deployer.versions()}
            self.publish_status(
                result["state"],
                f"Command {command} completed",
                {"request_id": request_id, **result},
            )
        except DeploymentRolledBack as exc:
            LOG.exception("Release was rolled back")
            self.publish_status(
                "rolled_back",
                str(exc),
                {"request_id": request_id, "command": command},
            )
        except (
            DeploymentError,
            OSError,
            ValueError,
            subprocess.SubprocessError,
        ) as exc:
            LOG.exception("Command failed")
            self.publish_status(
                "failed", str(exc), {"request_id": request_id, "command": command}
            )
        except Exception as exc:
            LOG.exception("Unexpected command failure")
            self.publish_status(
                "failed",
                f"Unexpected error: {type(exc).__name__}: {exc}",
                {"request_id": request_id, "command": command},
            )
        finally:
            self.worker_lock.release()

    def run(self) -> None:
        self.deployer.initialise()
        self.client.connect(self.config.mqtt_host, self.config.mqtt_port, keepalive=30)
        self.client.loop_forever(retry_first_connection=True)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    agent = Agent(load_config())
    agent.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
