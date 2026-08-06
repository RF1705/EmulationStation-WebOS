#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
vcpkg_root="${VCPKG_ROOT:-$repo_root/vcpkg}"
triplet="${VCPKG_TARGET_TRIPLET:-arm-webos}"

if [[ ! -x "$vcpkg_root/vcpkg" ]]; then
  echo "vcpkg executable not found at $vcpkg_root/vcpkg" >&2
  exit 1
fi
if [[ -z "${WEBOS_CHAINLOAD_TOOLCHAIN:-}" ]]; then
  echo "WEBOS_CHAINLOAD_TOOLCHAIN is not set." >&2
  exit 1
fi

export VCPKG_FORCE_SYSTEM_BINARIES=1
export VCPKG_DISABLE_METRICS=1

"$vcpkg_root/vcpkg" install \
  curl \
  ffmpeg \
  freeimage \
  freetype \
  gettext \
  harfbuzz \
  icu \
  libgit2 \
  "poppler[cpp]" \
  pugixml \
  --triplet "$triplet" \
  --overlay-triplets "$repo_root/vcpkg-triplets"
