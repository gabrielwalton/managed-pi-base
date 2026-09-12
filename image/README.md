# Building the reusable image

The image definition uses Raspberry Pi's official `rpi-image-gen` project. Its supported build host is a Raspberry Pi or another arm64 Debian Bookworm/Trixie system.

On that build host:

```sh
git clone https://github.com/raspberrypi/rpi-image-gen.git
cd rpi-image-gen
sudo ./install_deps.sh
cd ..
git clone https://github.com/gabrielwalton/managed-pi-base.git
./managed-pi-base/image/build.sh ./rpi-image-gen rpi5
```

Use `rpi4`, `rpi3`, or `rpizero2w` as the second argument for another supported board family.

The resulting image contains the agent and first-boot service but no credentials. Before first boot, copy a completed `managed-pi.env` onto the image's boot partition. The file may use `MANAGED_PI_DEVICE_ID=auto`, which derives a unique MQTT identity from the Pi hardware even when the same image is flashed repeatedly.

The first-boot service moves the secrets into `/etc/managed-pi/agent.env`, sets protected permissions, removes the boot-partition copy, and starts the agent. Home Assistant then discovers the Pi automatically through MQTT.

