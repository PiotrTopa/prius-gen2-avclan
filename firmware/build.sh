#!/usr/bin/env bash
# Build the AVC-LAN transceiver firmware.
#
#   ./build.sh                                   # RP2040-Zero (default)
#   PICO_BOARD=waveshare_rp2350_zero ./build.sh  # RP2350-Zero, same pinout
#
# Toolchain lookup order: $PICO_SDK_PATH and tools on $PATH, then the layout
# the official VS Code extension installs: ~/.pico-sdk/{sdk/<ver>,toolchain/<ver>/bin,cmake,ninja}.
set -euo pipefail
cd "$(dirname "$0")"

BOARD="${PICO_BOARD:-waveshare_rp2040_zero}"
PSDK_ROOT="${HOME}/.pico-sdk"

if [ -z "${PICO_SDK_PATH:-}" ]; then
    PICO_SDK_PATH="$(ls -d "${PSDK_ROOT}"/sdk/* 2>/dev/null | sort -V | tail -1 || true)"
    [ -n "$PICO_SDK_PATH" ] || { echo "PICO_SDK_PATH not set and no SDK under ${PSDK_ROOT}/sdk" >&2; exit 1; }
    export PICO_SDK_PATH
fi

if ! command -v arm-none-eabi-gcc >/dev/null 2>&1; then
    TC="$(ls -d "${PSDK_ROOT}"/toolchain/*/bin 2>/dev/null | sort -V | tail -1 || true)"
    [ -n "$TC" ] || { echo "arm-none-eabi-gcc not found" >&2; exit 1; }
    export PATH="${TC}:${PATH}"
fi
for tool in cmake ninja; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        for d in "${PSDK_ROOT}/venv/bin" "${PSDK_ROOT}"/"$tool"/*/bin "${PSDK_ROOT}"/"$tool"/*; do
            [ -x "$d/$tool" ] && { export PATH="$d:${PATH}"; break; }
        done
    fi
done

BUILD="build-${BOARD}"
cmake -S . -B "$BUILD" -G Ninja -DPICO_BOARD="$BOARD" -DCMAKE_BUILD_TYPE="${BUILD_TYPE:-Release}" "$@"
cmake --build "$BUILD" --parallel
echo
echo "UF2: $(pwd)/${BUILD}/avclan_rp2040.uf2"
