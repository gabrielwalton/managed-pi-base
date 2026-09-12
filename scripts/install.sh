#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this installer as root." >&2
  exit 1
fi

SOURCE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends cage chromium fonts-dejavu-core git python3 python3-venv ca-certificates sudo

if ! getent passwd managedpi >/dev/null; then
  useradd --system --create-home --home-dir /var/lib/managedpi --shell /usr/sbin/nologin managedpi
fi
usermod -a -G audio,input,render,video managedpi

install -d -m 0755 -o managedpi -g managedpi /opt/managed-pi
install -d -m 0750 -o managedpi -g managedpi /opt/managed-pi/cache /opt/managed-pi/releases /opt/managed-pi/data
install -d -m 0750 -o root -g managedpi /etc/managed-pi

rm -rf /opt/managed-pi/agent-source
install -d -m 0755 -o root -g root /opt/managed-pi/agent-source
cp -a "$SOURCE_DIR/src" "$SOURCE_DIR/pyproject.toml" /opt/managed-pi/agent-source/

python3 -m venv /opt/managed-pi/agent-venv
/opt/managed-pi/agent-venv/bin/pip install --disable-pip-version-check /opt/managed-pi/agent-source

install -m 0755 "$SOURCE_DIR/scripts/managed-pi-service-control" /usr/local/sbin/managed-pi-service-control
install -m 0755 "$SOURCE_DIR/scripts/managed-pi-kiosk" /usr/local/bin/managed-pi-kiosk
install -m 0755 "$SOURCE_DIR/scripts/managed-pi-firstboot" /usr/local/sbin/managed-pi-firstboot
install -m 0644 "$SOURCE_DIR/systemd/managed-pi-agent.service" /etc/systemd/system/managed-pi-agent.service
install -m 0644 "$SOURCE_DIR/systemd/managed-pi-app.service" /etc/systemd/system/managed-pi-app.service
install -m 0644 "$SOURCE_DIR/systemd/managed-pi-kiosk.service" /etc/systemd/system/managed-pi-kiosk.service
install -m 0644 "$SOURCE_DIR/systemd/managed-pi-firstboot.service" /etc/systemd/system/managed-pi-firstboot.service
install -m 0440 "$SOURCE_DIR/sudoers/managed-pi-service-control" /etc/sudoers.d/managed-pi-service-control
visudo -cf /etc/sudoers.d/managed-pi-service-control

systemctl daemon-reload
systemctl enable managed-pi-firstboot.service managed-pi-app.service managed-pi-kiosk.service

if [ -f /boot/firmware/managed-pi.env ]; then
  /usr/local/sbin/managed-pi-firstboot
elif [ -f /etc/managed-pi/agent.env ]; then
  systemctl enable --now managed-pi-agent.service
else
  echo "Installed. Add /boot/firmware/managed-pi.env and reboot to provision this Pi."
fi
