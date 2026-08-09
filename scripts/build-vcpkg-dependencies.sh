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

# Keep host tools native. The webOS cross compiler and sysroot are pinned in
# the chainload toolchain generated before invoking vcpkg.
export PATH="/usr/bin:/bin:$PATH"
unset CC CXX CPP CFLAGS CXXFLAGS LDFLAGS
unset AR AS LD NM OBJCOPY OBJDUMP RANLIB STRIP
unset CROSS_COMPILE ARCH KERNELDIR
unset PKG_CONFIG PKG_CONFIG_PATH PKG_CONFIG_LIBDIR PKG_CONFIG_SYSROOT_DIR
unset CONFIGURE_FLAGS
unset VCPKG_FORCE_SYSTEM_BINARIES
export VCPKG_DISABLE_METRICS=1

"$vcpkg_root/vcpkg" install \
  curl \
  freeimage \
  freetype \
  'libzip[core]' \
  rapidjson \
  --triplet "$triplet" \
  --overlay-triplets "$repo_root/vcpkg-triplets"
