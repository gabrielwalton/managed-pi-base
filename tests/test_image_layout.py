from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_image_allows_agent_to_switch_releases():
    layer = (ROOT / "layer" / "managed-pi-base.yaml").read_text(encoding="utf-8")
    assert "-o $(chroot $1 id -u managedpi)" in layer
    assert "$1/opt/managed-pi" in layer


def test_standard_installer_allows_agent_to_switch_releases():
    installer = (ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
    assert "install -d -m 0755 -o managedpi -g managedpi /opt/managed-pi" in installer


def test_app_inherits_managed_pi_identity_and_mqtt_settings():
    service = (ROOT / "systemd" / "managed-pi-app.service").read_text(encoding="utf-8")
    assert "EnvironmentFile=-/etc/managed-pi/agent.env" in service


def test_image_starts_the_hdmi_kiosk():
    layer = (ROOT / "layer" / "managed-pi-base.yaml").read_text(encoding="utf-8")
    assert "managed-pi-kiosk.service" in layer
    assert "chromium" in layer
    assert "cage" in layer


def test_agent_can_use_its_narrow_sudo_restart_rule():
    service = (ROOT / "systemd" / "managed-pi-agent.service").read_text(
        encoding="utf-8"
    )
    sudoers = (ROOT / "sudoers" / "managed-pi-service-control").read_text(
        encoding="utf-8"
    )
    assert "NoNewPrivileges=true" not in service
    assert "NOPASSWD: /usr/local/sbin/managed-pi-service-control restart" in sudoers


def test_reported_agent_version_matches_package_version():
    package = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    module = (ROOT / "src" / "managed_pi_agent" / "__init__.py").read_text(
        encoding="utf-8"
    )
    assert 'version = "0.3.2"' in package
    assert '__version__ = "0.3.2"' in module


def test_restart_does_not_wait_for_kiosk_shutdown_timeout():
    control = (ROOT / "scripts" / "managed-pi-service-control").read_text(
        encoding="utf-8"
    )
    kiosk = (ROOT / "systemd" / "managed-pi-kiosk.service").read_text(
        encoding="utf-8"
    )
    assert "--no-block restart managed-pi-app.service" in control
    assert "--no-block restart managed-pi-kiosk.service" in control
    assert "TimeoutStopSec=10" in kiosk


def test_kiosk_can_read_an_application_selected_url():
    kiosk = (ROOT / "scripts" / "managed-pi-kiosk").read_text(encoding="utf-8")
    assert "MANAGED_PI_KIOSK_URL_FILE" in kiosk
    assert 'http://*|https://*) kiosk_url="$requested_url"' in kiosk
    assert '"$kiosk_url"' in kiosk


def test_kiosk_routes_audio_to_the_connected_hdmi_output():
    kiosk = (ROOT / "scripts" / "managed-pi-kiosk").read_text(encoding="utf-8")
    assert "MANAGED_PI_ALSA_OUTPUT_DEVICE" in kiosk
    assert "^monitor_present[[:space:]]*1" in kiosk
    assert "^eld_valid[[:space:]]*1" in kiosk
    assert 'audio_device="plughw:${card_number},0"' in kiosk
    assert "--alsa-output-device=$audio_device" in kiosk
