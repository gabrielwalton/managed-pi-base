# Pi 4 field validation — 2026-09-13

Hardware validation used a Raspberry Pi 4 Model B on wired Ethernet with the
`v0.2.1` Pi 4 image.

## Confirmed on hardware

- The image boots headlessly and obtains its reserved network address.
- BOOT provisioning is consumed and the hardware-derived device ID stays stable
  across reflashes.
- The `0.2.1` management agent connects to MQTT and publishes Home Assistant
  Discovery entities.
- A GitHub release is downloaded and prepared without SSH or a local keyboard.
- The unprivileged agent can atomically select a release and invoke only its
  fixed sudo service-control helper.
- The application service restarts, passes its HTTP health check and reports the
  exact installed Git commit to Home Assistant.
- Application MQTT Discovery can share the protected connection settings without
  duplicating credentials in its repository.
- MQTT reconnect after a temporary keepalive timeout was observed.
- A requested application restart completed successfully and preserved the
  installed and previous release pointers.

## Defects found and fixed during validation

- `v0.2.0` corrected ownership of `/opt/managed-pi`, allowing the agent to switch
  the `current` and `previous` symlinks.
- `v0.2.1` removed `NoNewPrivileges` from the agent unit because that setting
  prevents Linux `sudo` from applying even the exact commands allowed by the
  root-owned sudoers rule. The application retains its own stricter sandbox.
- The first application now tests its exact production server entry point in CI;
  this caught launch-path assumptions before future deployment.
- Hardware testing found that a running Chromium tree could consume systemd's
  default 90-second stop timeout. The subsequent `v0.3.0` base requests service
  restarts asynchronously, limits kiosk shutdown to 10 seconds and caps MQTT
  reconnect delay at 15 seconds. These changes do not require an application to
  weaken its sandbox.

## Still to validate when the equipment is available

- HDMI kiosk rendering, video playback and audio on the target television.
- Deliberately unhealthy-release automatic rollback.
- Power interruption during release preparation.
- Retained-command rejection and concurrent-command locking on hardware.

These unchecked items do not change the provisioning format. Record their result
here before labelling a later release as fully production-accepted.
