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
- A deliberate requested rollback selected the previous healthy commit, passed
  its health check and reported the changed version; a following Update restored
  the latest commit successfully.

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
- Deliberately unhealthy-release automatic rollback (requested rollback is
  already confirmed).
- Power interruption during release preparation.
- Retained-command rejection and concurrent-command locking on hardware.

These unchecked items do not change the provisioning format. Record their result
here before labelling a later release as fully production-accepted.

## v0.3.0 reflash follow-up

The same Pi 4 was reflashed with the `v0.3.0` image and provisioned unattended
from the BOOT environment file. It reported agent version `0.3.0`, installed the
photo-viewer application from GitHub, retained its stable device identity and
completed a requested application/kiosk restart in 5.4 seconds. This confirms
the bounded, non-blocking restart fix resolved the earlier approximately
96-second restart delay.

The application then connected to an SMB library, indexed 20,001 media items,
served a byte-range request successfully and reported the changing current item
from the HDMI Chromium session. Direct visual confirmation of the external
display remains a separate human acceptance step.

## v0.3.1 clean-image follow-up

The Pi 4 was then clean-flashed with the `v0.3.1` image. It consumed a fresh
BOOT provisioning file, came online as agent `0.3.1`, and installed the
application without SSH, keyboard input or a local login. The application
retained its stable hardware-derived identity.

The dynamic kiosk target was exercised through Home Assistant in all three
application states: photos, collage and dashboard. Returning from dashboard to
the local viewer succeeded on the same HDMI session. An application restart
restored photo mode while preserving its private configuration, NAS credentials,
selected folder and a 38,336-item catalogue. Site-specific Home Assistant
trusted-network configuration remains deliberately outside the reusable image.

## v0.3.2 HDMI audio correction

Testing on the Samsung television confirmed that the display's HDMI audio device
was available and produced a direct ALSA test tone, while Chromium had selected
the Pi's analogue headphone output. Version 0.3.2 makes the kiosk launcher inspect
the kernel HDMI ELD state at each start and pass the connected HDMI ALSA device to
Chromium explicitly. This remains to be confirmed with video playback after the
0.3.2 image is flashed.
