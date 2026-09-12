# First-device acceptance checklist

Complete these checks on the first physical Pi before treating the image as reusable.

## Provisioning

- Flash the generated image.
- Place a completed `managed-pi.env` on the boot partition.
- Connect Ethernet and power on.
- Confirm the provisioning file disappears from the boot partition.
- Confirm `/etc/managed-pi/agent.env` is owned by `root:managedpi` and mode `0640`.
- Confirm `managed-pi-agent.service` is active.

## Home Assistant discovery

- Confirm one new Managed Pi device appears automatically.
- Confirm availability is online.
- Confirm Update, Check, Roll Back and Restart buttons exist.
- Confirm status and version sensors exist.
- Confirm restarting Home Assistant does not replay an update.

## First application deployment

- Press Check and confirm `update_available` is reported.
- Press Update and confirm the exact Git commit appears as the installed version.
- Confirm `managed-pi-app.service` is active.
- Confirm the application's own health check passes.
- Press Update again and confirm `up_to_date` without a restart.

## Rollback proof

- Deploy a deliberately unhealthy test commit whose health check exits non-zero.
- Confirm the agent reports `rolled_back`.
- Confirm the previous application is running and healthy.
- Confirm the failed commit is not selected by `/opt/managed-pi/current`.
- Deploy a corrected commit and confirm recovery without SSH.
- Press Roll Back and confirm a deliberate rollback also succeeds.

## Security and resilience

- Publish a retained `update` command and confirm it is ignored.
- Send an unknown command and confirm `command_rejected`.
- Trigger two updates together and confirm one reports `busy`.
- Disconnect MQTT temporarily and confirm availability changes to offline, then recovers.
- Disconnect power during release preparation and confirm the previous `current` release still boots.
- Confirm the application cannot write outside `/opt/managed-pi/data`.
- Confirm `managedpi` can run only the two allowed service-control operations through passwordless sudo.

