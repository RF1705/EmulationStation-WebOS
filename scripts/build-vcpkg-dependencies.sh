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
if [[ ! -x /usr/bin/cmake ]]; then
  echo "Host CMake not found at /usr/bin/cmake" >&2
  exit 1
fi

# The webOS SDK prepends its own host utilities to PATH. Its bundled CMake is
# linked against OpenSSL 1.1, which is unavailable on current Ubuntu runners.
# Prefer the runner's native build tools; the ARM cross tools remain available
# later in PATH and are selected explicitly by the chainload toolchain.
export PATH="/usr/bin:/bin:$PATH"
export VCPKG_FORCE_SYSTEM_BINARIES=1
export VCPKG_DISABLE_METRICS=1

echo "Using host CMake: $(command -v cmake)"
cmake --version | head -n 1

"$vcpkg_root/vcpkg" install \
  curl \
  ffmpeg \
  freeimage \
  freetype \
  gettext \
  harfbuzz \
  icu \
  libgit2 \
  poppler \
  pugixml \
  --triplet "$triplet" \
  --overlay-triplets "$repo_root/vcpkg-triplets"
