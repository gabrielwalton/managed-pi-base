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
