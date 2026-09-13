# Starting a new Managed Pi project

This is the repeatable path for a new Raspberry Pi project. It does not require
SSH, a keyboard or a project-specific operating-system image.

## 1. Prepare the application repository

Create a GitHub repository whose default branch contains:

- `deploy/install.sh` to create release-local dependencies or build assets;
- `deploy/run.sh` to run one foreground process and remain attached to it;
- `deploy/healthcheck.sh` to return zero only when the application is usable.

The process runs as `managedpi`. Persistent application data belongs below
`/opt/managed-pi/data`; a release must not depend on writing into its own source
directory. For Python web services, prefer a checked-in `python -m package.server`
entry point and exercise that exact entry point in CI.

Operating-system packages cannot be installed by an application hook. Add any
shared package to the base image in a reviewed release, or deliberately create a
separate base-image variant when the dependency is specialised.

## 2. Create the provisioning file

Copy `provision.env.example` to `managed-pi.env` outside Git and set:

- a human-readable device name and short project prefix;
- the Home Assistant MQTT address and credentials;
- the HTTPS GitHub repository and branch;
- `MANAGED_PI_DEVICE_ID=auto` so the Pi serial creates a stable unique identity.

Do not commit this file. Public repositories require no GitHub credential. Use a
repository-scoped, read-only deploy key for a private application.

## 3. Flash and provision

1. Download the correct board asset from a Managed Pi Base GitHub release.
2. In Raspberry Pi Imager choose **Use custom** and select the `.img.xz` file.
3. Write and verify the SD card.
4. Reopen the small FAT partition labelled **BOOT**.
5. Copy `managed-pi.env` into the top level of BOOT.
6. Safely eject, insert the card into the Pi, connect Ethernet and power on.

If Windows sees BOOT but gives it no drive letter, use Disk Management as an
administrator: identify the removable card by its exact capacity, right-click
its approximately 100 MB FAT partition, and assign an unused drive letter. Never
choose a partition by disk number copied from another session because numbers
can change when devices are reinserted.

At first boot the file is moved to protected Linux storage and removed from the
Windows-readable partition. Re-copy it after every full reflash.

## 4. Deploy and operate

Home Assistant MQTT Discovery creates one Managed Pi device with Check, Update,
Restart and Roll Back buttons plus status and installed-version sensors. Press
Update once to install the first application release. Later releases require
only a tested push to GitHub followed by that same button.

Updates are prepared away from the active release, selected atomically, restarted
through a fixed root-owned helper and verified by both systemd and the repository
health check. A failed update returns to the prior healthy release when one exists.

## 5. Project handoff checklist

- Keep the completed provisioning file in secure local storage.
- Record the GitHub repository, device ID and reserved IP in the project notes.
- Add a CI test that runs the production entry point and calls its health URL.
- Test Update, Restart, Roll Back and recovery to latest on the physical Pi.
- Test loss and restoration of MQTT and power before unattended deployment.
- For HDMI projects, verify the kiosk at the target resolution and check audio,
  video codecs and HDMI-CEC behaviour on the actual display.
