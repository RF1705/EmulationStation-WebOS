#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${BUILD_DIR:-$repo_root/build/es-de}"
dist_dir="${DIST_DIR:-$repo_root/dist}"
package_dir="$dist_dir/package"
stage_dir="$dist_dir/stage"
deps_prefix="${WEBOS_DEPS_PREFIX:-$repo_root/build/webos-deps}"
vcpkg_root="${VCPKG_ROOT:-$repo_root/vcpkg}"
triplet="${VCPKG_TARGET_TRIPLET:-arm-webos}"
install_prefix="${WEBOS_INSTALL_PREFIX:-/usr/palm/applications/com.rf1705.esde}"
version="${WEBOS_PACKAGE_VERSION:-3.4.1}"
host_cmake="${HOST_CMAKE:-/usr/bin/cmake}"

for command in ares-package rsvg-convert; do
  command -v "$command" >/dev/null 2>&1 || { echo "$command is required." >&2; exit 1; }
done
[[ -x "$host_cmake" ]] || { echo "Host CMake not found at $host_cmake" >&2; exit 1; }
for variable in CC STAGING_DIR SDL2_BUNDLE_DIR; do
  [[ -n "${!variable:-}" ]] || { echo "$variable is not set." >&2; exit 1; }
done
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "Invalid package version: $version" >&2; exit 1; }

rm -rf "$dist_dir"
mkdir -p "$package_dir/lib" "$stage_dir"
DESTDIR="$stage_dir" "$host_cmake" --install "$build_dir"
installed="$stage_dir$install_prefix"
[[ -d "$installed" ]] || { echo "Installed ES-DE tree not found at $installed" >&2; exit 1; }
cp -a "$installed"/. "$package_dir/"

binary="$(find "$package_dir" -type f -name es-de -perm -111 -print -quit)"
[[ -n "$binary" ]] || { echo "Installed ES-DE binary was not found." >&2; exit 1; }
mv "$binary" "$package_dir/es-de.bin"

"$CC" -Os -s "$repo_root/packaging/launch-esde.c" -o "$package_dir/es-de"
sed "s/@VERSION@/$version/g" "$repo_root/packaging/appinfo.json.in" > "$package_dir/appinfo.json"
rsvg-convert -w 160 -h 160 "$repo_root/packaging/icon.svg" -o "$package_dir/icon160.png"

copy_shared_libraries() {
  local root="$1"
  [[ -d "$root" ]] || return 0
  while IFS= read -r library; do
    cp -L "$library" "$package_dir/lib/$(basename "$library")"
  done < <(find -L "$root" -maxdepth 3 -type f -name '*.so*' -print)
}
copy_shared_libraries "$deps_prefix/lib"
copy_shared_libraries "$vcpkg_root/installed/$triplet/lib"

sdl_library="$(find "$SDL2_BUNDLE_DIR" -name 'libSDL2-2.0.so.0' -print -quit)"
[[ -n "$sdl_library" ]] || { echo "SDL-webOS runtime library was not found." >&2; exit 1; }
cp -L "$sdl_library" "$package_dir/lib/libSDL2-2.0.so.0"

for name in libstdc++.so.6 libatomic.so.1 libgcc_s.so.1; do
  path="$(find "$STAGING_DIR" -name "$name" -print -quit)"
  [[ -z "$path" ]] || cp -L "$path" "$package_dir/lib/$name"
done

find "$package_dir" -type f -perm -111 -exec "${STRIP:-strip}" {} + 2>/dev/null || true
(
  cd "$dist_dir"
  ares-package package
)
ipk="$(find "$dist_dir" -maxdepth 1 -name '*.ipk' -print -quit)"
[[ -n "$ipk" ]] || { echo "ares-package did not produce an IPK." >&2; exit 1; }

if [[ -n "${WEBOS_BUILD_SUFFIX:-}" ]]; then
  renamed="$dist_dir/com.rf1705.esde_${version}-${WEBOS_BUILD_SUFFIX}_arm.ipk"
  mv "$ipk" "$renamed"
  ipk="$renamed"
fi
(
  cd "$(dirname "$ipk")"
  sha256sum "$(basename "$ipk")"
) > "$ipk.sha256"

echo "PACKAGE_PATH=$ipk"
