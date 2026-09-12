#!/bin/sh
set -eu

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "Usage: $0 /path/to/rpi-image-gen [rpi5|rpi4|rpi3|rpizero2w]" >&2
  exit 64
fi

IMAGE_GEN=$(CDPATH= cd -- "$1" && pwd)
DEVICE=${2:-rpi5}
SOURCE=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

case "$DEVICE" in
  rpi5|rpi4|rpi3|rpizero2w) ;;
  *)
    echo "Unsupported device layer: $DEVICE" >&2
    exit 64
    ;;
esac

exec "$IMAGE_GEN/rpi-image-gen" build -S "$SOURCE" -c "$SOURCE/image/managed-pi.yaml" -- "IGconf_device_layer=$DEVICE"

