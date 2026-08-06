#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_dir="${ESDE_SOURCE_DIR:-$repo_root/upstream}"
build_dir="${BUILD_DIR:-$repo_root/build/es-de}"
deps_prefix="${WEBOS_DEPS_PREFIX:-$repo_root/build/webos-deps}"
vcpkg_root="${VCPKG_ROOT:-$repo_root/vcpkg}"
triplet="${VCPKG_TARGET_TRIPLET:-arm-webos}"
install_prefix="${WEBOS_INSTALL_PREFIX:-/usr/palm/applications/com.rf1705.esde}"
host_cmake="${HOST_CMAKE:-/usr/bin/cmake}"

for variable in CC CXX STAGING_DIR WEBOS_CHAINLOAD_TOOLCHAIN SDL2_BUNDLE_DIR; do
  if [[ -z "${!variable:-}" ]]; then
    echo "$variable is not set." >&2
    exit 1
  fi
done
if [[ ! -x "$host_cmake" ]]; then
  echo "Host CMake not found at $host_cmake" >&2
  exit 1
fi
if [[ ! -f "$source_dir/CMakeLists.txt" ]]; then
  echo "ES-DE source not found at $source_dir" >&2
  exit 1
fi
if [[ ! -f "$vcpkg_root/scripts/buildsystems/vcpkg.cmake" ]]; then
  echo "vcpkg toolchain not found below $vcpkg_root" >&2
  exit 1
fi

python3 "$repo_root/scripts/patch-esde-webos.py" "$source_dir"

sdl_include="$(find "$SDL2_BUNDLE_DIR" -path '*/include/SDL2/SDL.h' -print -quit)"
sdl_library="$(find "$SDL2_BUNDLE_DIR" -name 'libSDL2-2.0.so.0' -print -quit)"
if [[ -z "$sdl_include" || -z "$sdl_library" ]]; then
  echo "SDL-webOS headers or library were not found below $SDL2_BUNDLE_DIR" >&2
  exit 1
fi
sdl_include="$(dirname "$sdl_include")"

vcpkg_prefix="$vcpkg_root/installed/$triplet"
freeimage_include="$vcpkg_prefix/include"
freeimage_library="$(find "$vcpkg_prefix/lib" -maxdepth 1 -type f \( -name 'libfreeimage.so' -o -name 'libfreeimage.a' \) -print -quit)"
if [[ ! -f "$freeimage_include/FreeImage.h" || -z "$freeimage_library" ]]; then
  echo "FreeImage headers or library were not found below $vcpkg_prefix" >&2
  exit 1
fi

export PKG_CONFIG_ALLOW_CROSS=1
export PKG_CONFIG_SYSROOT_DIR=""
export PKG_CONFIG_LIBDIR="$deps_prefix/lib/pkgconfig:$deps_prefix/share/pkgconfig:$vcpkg_prefix/lib/pkgconfig:$vcpkg_prefix/share/pkgconfig"
unset PKG_CONFIG_PATH

rm -rf "$build_dir"
mkdir -p "$build_dir"

"$host_cmake" -S "$source_dir" -B "$build_dir" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_TOOLCHAIN_FILE="$vcpkg_root/scripts/buildsystems/vcpkg.cmake" \
  -DVCPKG_TARGET_TRIPLET="$triplet" \
  -DVCPKG_OVERLAY_TRIPLETS="$repo_root/vcpkg-triplets" \
  -DCMAKE_INSTALL_PREFIX="$install_prefix" \
  -DCMAKE_PREFIX_PATH="$deps_prefix;$vcpkg_prefix" \
  '-DCMAKE_INSTALL_RPATH=$ORIGIN/lib' \
  '-DCMAKE_BUILD_RPATH=$ORIGIN/lib' \
  -DCMAKE_EXE_LINKER_FLAGS="${LDFLAGS:-} -Wl,--gc-sections" \
  -DCMAKE_C_FLAGS="${CFLAGS:-} -Os -ffunction-sections -fdata-sections -mcpu=cortex-a9 -mfloat-abi=softfp -mfpu=neon" \
  -DCMAKE_CXX_FLAGS="${CXXFLAGS:-} -Os -ffunction-sections -fdata-sections -mcpu=cortex-a9 -mfloat-abi=softfp -mfpu=neon" \
  -DGL=OFF \
  -DGLES=ON \
  -DWEBOS=ON \
  -DAPPLICATION_UPDATER=OFF \
  -DCOMPILE_LOCALIZATIONS=OFF \
  -DDEINIT_ON_LAUNCH=ON \
  -DVIDEO_HW_DECODING=OFF \
  -DCEC=OFF \
  -DFreeImage_INCLUDE_DIR="$freeimage_include" \
  -DFreeImage_LIBRARY_REL="$freeimage_library" \
  -DFreeImage_LIBRARY="$freeimage_library" \
  -DSDL2_INCLUDE_DIR="$sdl_include" \
  -DSDL2_INCLUDE_DIRS="$sdl_include" \
  -DSDL2_LIBRARY="$sdl_library" \
  -DSDL2_LIBRARIES="$sdl_library"

"$host_cmake" --build "$build_dir" --parallel "${JOBS:-$(getconf _NPROCESSORS_ONLN)}"

binary="$(find "$build_dir" -type f -name es-de -perm -111 -print -quit)"
if [[ -z "$binary" ]]; then
  echo "ES-DE binary was not produced." >&2
  exit 1
fi

"${STRIP:-strip}" "$binary" || true
file "$binary"
"${READELF:-readelf}" -d "$binary" | grep -E 'NEEDED|RPATH|RUNPATH' || true
