# Managed Pi Base

A reusable Raspberry Pi foundation for deploying an application from GitHub by pressing a button in Home Assistant.

The image also includes a television kiosk layer. When an installed application
serves a page on port 8080, Chromium starts it fullscreen on HDMI with video
autoplay enabled; no desktop, keyboard or local login is required.

This project generalises the working SolarPi flow:

1. Home Assistant publishes a non-retained MQTT command.
2. A persistent Pi agent fetches the configured GitHub branch.
3. The new commit is prepared in a separate release directory.
4. The application is restarted through a narrowly scoped service-control helper.
5. Both systemd and the application's own health check must pass.
6. A failed release is automatically rolled back.
7. Progress, versions and failures are retained in MQTT for Home Assistant.

Unlike the first SolarPi implementation, source releases and their dependencies are kept together. Rolling back therefore restores both code and its release-local Python environment.

## Home Assistant

The agent uses MQTT Discovery. Once a provisioned Pi connects, Home Assistant automatically creates one device containing:

- Update application
- Check for update
- Roll back application
- Restart application
- Update status
- Installed version

No per-Pi helper buttons or forwarding automations are required.

## Application contract

Every managed application repository must contain:

- `deploy/run.sh` — starts the foreground application process.
- `deploy/healthcheck.sh` — exits zero only when the application is genuinely healthy.
- `deploy/install.sh` — optional release-local dependency/build step.

See `examples/app/deploy`.

Application hooks run as the unprivileged `managedpi` account. They cannot install operating-system packages or rewrite system services. Common OS dependencies should be included in the base image; unusual privileged changes require a reviewed base-image update.

For the complete repeatable workflow, including Windows flashing and a new
application checklist, see [Starting a new Managed Pi project](docs/new-project.md).

## One-time installation on a standard Raspberry Pi OS image

Clone this repository on the Pi and run:

```sh
sudo ./scripts/install.sh
```

Then copy `provision.env.example` to `managed-pi.env`, fill in the local values, and place it on the SD card boot partition at `/boot/firmware/managed-pi.env`. On the next boot it is moved to `/etc/managed-pi/agent.env` with protected permissions and removed from the boot partition.

The normal route is now the released reusable image. The manual installer is a
development and recovery option; future Pis need only the image and their small
provisioning file.

## Update topics

For device `photo-viewer-1`:

- Command: `managed-pi/photo-viewer-1/command`
- Status: `managed-pi/photo-viewer-1/status`
- Version: `managed-pi/photo-viewer-1/version`
- Availability: `managed-pi/photo-viewer-1/availability`

Accepted commands are `check`, `update`, `rollback`, `restart`, and `status`. Commands may be plain text or JSON with `command` and `request_id`. Retained commands are ignored so an old update cannot replay after a reboot.

The HDMI kiosk normally opens `MANAGED_PI_VIEWER_URL`. An application can request a
different full-screen page by writing one `http://` or `https://` URL to
`/opt/managed-pi/data/kiosk-url` and terminating its own Chromium process. The kiosk
service restarts Chromium and reads the requested URL. Applications should restore
their local viewer URL when they start so a reboot always has a safe default.

## Security boundaries

- MQTT credentials and private GitHub keys are never stored in this repository.
- The updater and application run as the dedicated `managedpi` user.
- Only a root-owned wrapper may restart or inspect `managed-pi-app.service`.
- Application releases are immutable directories selected through an atomic `current` symlink.
- A release is activated only after its installation hook succeeds.
- Failed restart or health checks restore the previous known-good release.
- Public HTTPS repositories need no GitHub credential on the Pi. Private repositories should use a read-only deploy key dedicated to that single repository.

## Current status

The management agent, atomic release deployment, automatic rollback, HDMI kiosk,
system services, first-boot secret migration, MQTT Discovery, configuration
validation and reproducible Pi 4/Pi 5 images are implemented. Applications can
also inherit the Pi's MQTT identity and connection without duplicating secrets.
The Pi 4 image has completed real-hardware provisioning and application-update
validation; the remaining optional acceptance checks are tracked in
[the field validation record](docs/field-validation-2026-09-13.md).
