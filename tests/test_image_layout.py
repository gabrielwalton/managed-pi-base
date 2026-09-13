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
    assert 'version = "0.2.1"' in package
    assert '__version__ = "0.2.1"' in module
