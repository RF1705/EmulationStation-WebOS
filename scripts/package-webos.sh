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
readelf_cmd="${READELF:-readelf}"

for command in ares-package rsvg-convert; do
  command -v "$command" >/dev/null 2>&1 || { echo "$command is required." >&2; exit 1; }
done
[[ -x "$host_cmake" ]] || { echo "Host CMake not found at $host_cmake" >&2; exit 1; }
command -v "$readelf_cmd" >/dev/null 2>&1 || [[ -x "$readelf_cmd" ]] || { echo "readelf is required." >&2; exit 1; }
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

# ES-DE normally resolves resources and themes from CMAKE_INSTALL_PREFIX.
# Developer-mode webOS apps are physically installed below /media/developer/apps,
# so that compiled prefix does not point at the real files. Put both directories
# next to the executable; this is another documented ES-DE lookup location and
# works independently of the webOS install base path.
resources_source="$package_dir/share/es-de/resources"
themes_source="$package_dir/share/es-de/themes"
[[ -d "$resources_source" ]] || { echo "ES-DE resources were not installed." >&2; exit 1; }
[[ -d "$themes_source/linear-es-de" ]] || { echo "Default Linear theme was not installed." >&2; exit 1; }

# ES-DE installs Linear, Modern and Slate on generic Unix targets. Linear is
# the ES-DE 3.x default theme and is sufficient for first startup on webOS.
rm -rf "$themes_source/modern-es-de" "$themes_source/slate-es-de"

rm -rf "$package_dir/resources" "$package_dir/themes"
mv "$resources_source" "$package_dir/resources"
mv "$themes_source" "$package_dir/themes"

# en_US is ES-DE's mandatory fallback locale. Fail packaging instead of creating
# an IPK that installs successfully but immediately aborts during startup.
locale_catalog="$package_dir/resources/locale/en_US/LC_MESSAGES/en_US.mo"
[[ -f "$locale_catalog" ]] || { echo "Required ES-DE locale catalog missing: $locale_catalog" >&2; exit 1; }

echo "Bundled executable-relative ES-DE resources and Linear theme"
du -sh "$package_dir/resources" "$package_dir/themes" || true

binary="$(find "$package_dir" -type f -name es-de -perm -111 -print -quit)"
[[ -n "$binary" ]] || { echo "Installed ES-DE binary was not found." >&2; exit 1; }
mv "$binary" "$package_dir/es-de.bin"

"$CC" -Os -s "$repo_root/packaging/launch-esde.c" -o "$package_dir/es-de"
sed "s/@VERSION@/$version/g" "$repo_root/packaging/appinfo.json.in" > "$package_dir/appinfo.json"
rsvg-convert -w 160 -h 160 "$repo_root/packaging/icon.svg" -o "$package_dir/icon160.png"

# Bundle only the recursive DT_NEEDED closure required by the installed ELF
# executables. The previous implementation copied every vcpkg .so and followed
# symlink chains, turning aliases such as libicudata.so, libicudata.so.78 and
# libicudata.so.78.3 into three full copies of the same library.
vcpkg_lib="$vcpkg_root/installed/$triplet/lib"
search_roots=(
  "$deps_prefix/lib"
  "$vcpkg_lib"
  "$vcpkg_lib/manual-link"
  "$SDL2_BUNDLE_DIR/lib"
)

declare -A processed_elf=()
declare -A bundled_library=()
queue=()

is_system_library() {
  case "$1" in
    ld-linux*.so*|libc.so.*|libm.so.*|libdl.so.*|libpthread.so.*|librt.so.*|libresolv.so.*|libutil.so.*|libnsl.so.*|libcrypt.so.*|libbz2.so.*|libGLESv2.so*|libEGL.so*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

resolve_library() {
  local name="$1"
  local root path

  if [[ -e "$package_dir/lib/$name" ]]; then
    printf '%s\n' "$package_dir/lib/$name"
    return 0
  fi

  for root in "${search_roots[@]}"; do
    [[ -d "$root" ]] || continue
    path="$(find "$root" -maxdepth 3 -name "$name" -print -quit)"
    if [[ -n "$path" ]]; then
      printf '%s\n' "$path"
      return 0
    fi
  done

  # C++/GCC runtime libraries come from the webOS SDK rather than vcpkg.
  case "$name" in
    libstdc++.so.*|libgcc_s.so.*|libatomic.so.*)
      path="$(find "$STAGING_DIR" -name "$name" -print -quit)"
      if [[ -n "$path" ]]; then
        printf '%s\n' "$path"
        return 0
      fi
      ;;
  esac

  return 1
}

enqueue_elf() {
  local path="$1"
  [[ -f "$path" ]] || return 0
  if "$readelf_cmd" -h "$path" >/dev/null 2>&1; then
    queue+=("$path")
  fi
}

# Seed the dependency walk with every installed executable/helper ELF.
while IFS= read -r executable; do
  enqueue_elf "$executable"
done < <(find "$package_dir" -type f -perm -111 -print)

queue_index=0
while (( queue_index < ${#queue[@]} )); do
  elf="${queue[$queue_index]}"
  ((queue_index += 1))

  [[ -z "${processed_elf[$elf]:-}" ]] || continue
  processed_elf["$elf"]=1

  while IFS= read -r needed; do
    [[ -n "$needed" ]] || continue
    is_system_library "$needed" && continue
    [[ -z "${bundled_library[$needed]:-}" ]] || continue

    if ! source_library="$(resolve_library "$needed")"; then
      echo "Required runtime library $needed (needed by $elf) was not found." >&2
      echo "Searched dependency roots:" >&2
      printf '  %s\n' "${search_roots[@]}" >&2
      exit 1
    fi

    destination="$package_dir/lib/$needed"
    if [[ "$source_library" != "$destination" ]]; then
      cp -L "$source_library" "$destination"
    fi
    bundled_library["$needed"]=1
    echo "Bundled runtime library: $needed"
    enqueue_elf "$destination"
  done < <("$readelf_cmd" -d "$elf" 2>/dev/null | sed -n 's/.*Shared library: \[\([^]]*\)\].*/\1/p')
done

# Strip every packaged ELF, not only files with an executable permission bit.
# Many shared libraries are installed mode 0644, so the old -perm -111 filter
# left their symbol/debug tables untouched. --strip-unneeded keeps the dynamic
# symbols required by the loader while dropping build/debug-only sections.
strip_cmd="${STRIP:-strip}"
stripped_count=0
while IFS= read -r elf_file; do
  if "$readelf_cmd" -h "$elf_file" >/dev/null 2>&1; then
    "$strip_cmd" --strip-unneeded "$elf_file"
    ((stripped_count += 1))
  fi
done < <(find "$package_dir" -type f -print)
echo "Stripped ELF files: $stripped_count"

echo "Packaged runtime libraries: ${#bundled_library[@]}"
du -sh "$package_dir/lib" "$package_dir" || true

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
  ls -lh "$(basename "$ipk")"
) > "$ipk.sha256"

ls -lh "$ipk"
echo "PACKAGE_PATH=$ipk"
