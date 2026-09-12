# SolarPi lessons carried forward

The earlier Axpert Gateway/SolarPi project established the deployment route used as the starting point for this base.

## Confirmed working SolarPi pattern

- Repository: `gabrielwalton/axpert-gateway`, deploying its `main` branch.
- Pi application directory: `/opt/axpert-gateway`.
- Home Assistant published `update` to `axpert-gateway/control/update` with QoS 1 and no retain.
- A persistent MQTT updater on the Pi received the command.
- The updater handed work to a separate update worker rather than replacing itself inside the MQTT callback.
- The worker used a lock to reject concurrent deployments.
- It refused to deploy over a dirty Git working tree.
- It fetched `origin/main`, recorded the previous commit, validated Python, restarted the service, checked systemd health and reset to the previous commit on failure.
- Home Assistant captured retained status and version messages for remote verification.
- A restricted patch receiver was later used because direct SSH access was unavailable. It accepted structured file changes, checked the expected base commit and allowed paths, and rejected arbitrary shell commands.

The old task also confirmed that the original SSH account was `axpert` and the host was reachable as `axpert-gateway.local`. Its exact original unit files, sudoers rule, ownership setup and deploy-key location were not retained in the Git repository, so this project does not copy unverifiable details.

## Problems corrected here

- SolarPi used two inconsistent update-status topics and payload formats. Managed Pi uses one retained JSON status topic.
- SolarPi changed a live Git working tree in place. Managed Pi prepares a separate immutable release and changes one symlink atomically.
- SolarPi source rollback did not necessarily undo changed dependencies. Managed Pi keeps dependencies inside each release.
- SolarPi required manually created Home Assistant helpers and automations. Managed Pi publishes MQTT Discovery definitions.
- Managed Pi ignores retained control messages, preventing an old update from replaying after reconnection.
- Managed Pi application hooks run without root privileges. The only passwordless root action is a fixed wrapper that restarts or inspects one fixed service.
- The reusable image derives a unique device identity from Raspberry Pi hardware, avoiding topic collisions when the same image is flashed more than once.

## Deliberately not copied

The SolarPi restricted source-patch receiver is not part of the normal Managed Pi route. GitHub is the source of truth: changes are developed, tested, reviewed and merged there, then the Pi pulls an exact commit. This is simpler to audit and avoids opening a generic remote file-writing channel over MQTT.

