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

# The webOS SDK prepends old host utilities and exports ARM compilers globally.
# Keep its bin directory in PATH for the target toolchain, but prefer native
# runner tools for host builds. The generated chainload file contains absolute
# paths to the ARM compiler, sysroot and flags, so clearing these variables here
# does not affect target builds.
export PATH="/usr/bin:/bin:$PATH"
unset CC CXX CPP CFLAGS CXXFLAGS LDFLAGS
unset AR AS LD NM OBJCOPY OBJDUMP RANLIB STRIP
unset CROSS_COMPILE ARCH KERNELDIR
unset PKG_CONFIG PKG_CONFIG_PATH PKG_CONFIG_LIBDIR PKG_CONFIG_SYSROOT_DIR
unset CONFIGURE_FLAGS

# Current vcpkg scripts require a newer CMake than Ubuntu 24.04 provides.
# Do not force system binaries: vcpkg will acquire a compatible host CMake and
# other helper tools itself when the installed versions are too old.
unset VCPKG_FORCE_SYSTEM_BINARIES
export VCPKG_DISABLE_METRICS=1

echo "Host compiler: $(command -v c++)"
echo "Initial host CMake: $(command -v cmake)"
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
