#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_dir="${EMULATIONSTATION_SOURCE_DIR:-$repo_root}"
dist_dir="${DIST_DIR:-$repo_root/dist}"
package_dir="$dist_dir/package"
vcpkg_root="${VCPKG_ROOT:-$repo_root/vcpkg}"
triplet="${VCPKG_TARGET_TRIPLET:-arm-webos}"
version="${WEBOS_PACKAGE_VERSION:-1.0.0}"
readelf_cmd="${READELF:-readelf}"

for command in ares-package rsvg-convert python3; do
  command -v "$command" >/dev/null 2>&1 || { echo "$command is required." >&2; exit 1; }
done
command -v "$readelf_cmd" >/dev/null 2>&1 || [[ -x "$readelf_cmd" ]] || { echo "readelf is required." >&2; exit 1; }
for variable in CC STAGING_DIR SDL2_BUNDLE_DIR; do
  [[ -n "${!variable:-}" ]] || { echo "$variable is not set." >&2; exit 1; }
done
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "Invalid package version: $version" >&2; exit 1; }

binary="$source_dir/emulationstation"
[[ -x "$binary" ]] || { echo "Built EmulationStation binary not found at $binary" >&2; exit 1; }
[[ -d "$source_dir/resources" ]] || { echo "RetroPie resources directory not found." >&2; exit 1; }

rm -rf "$dist_dir"
mkdir -p "$package_dir/lib"
cp "$binary" "$package_dir/emulationstation.bin"
cp -a "$source_dir/resources" "$package_dir/resources"
cp "$repo_root/packaging/es_systems.cfg" "$package_dir/default-es_systems.cfg"

# The pinned Simple Dark archive contains artwork for systems that have no
# usable RetroArch core on webOS. Keep the complete archive in the repository,
# but ship the shared assets plus platforms represented by the webosbrew ARMv7
# core feed. Duplicate regional theme names (for example Genesis/Mega Drive or
# Famicom/NES) stay available so user-defined systems can use either naming.
bundled_theme_source="$source_dir/resources/bundled-themes/simple-dark.zip"
bundled_theme_package="$package_dir/resources/bundled-themes/simple-dark.zip"
if [[ -f "$bundled_theme_source" && -f "$bundled_theme_package" ]]; then
  python3 - "$bundled_theme_source" "$bundled_theme_package" <<'PY'
import os
import sys
import zipfile

source_path, destination_path = sys.argv[1:3]
keep_dirs = {
    "art",
    "3do",
    "amiga",
    "amstradcpc",
    "apple2",
    "arcade",
    "atari2600",
    "atari5200",
    "atari7800",
    "atari800",
    "atarifalcon",
    "atarijaguar",
    "atarilynx",
    "atarist",
    "atarixe",
    "c64",
    "colecovision",
    "daphne",
    "dreamcast",
    "famicom",
    "fba",
    "gamegear",
    "gb",
    "gba",
    "gbc",
    "genesis",
    "intellivision",
    "macintosh",
    "mame",
    "mastersystem",
    "megadrive",
    "moto",
    "msx",
    "n64",
    "nds",
    "neogeo",
    "nes",
    "ngp",
    "ngpc",
    "odyssey2",
    "pc",
    "pcengine",
    "ports",
    "psp",
    "psx",
    "saturn",
    "scummvm",
    "sega32x",
    "segacd",
    "sfc",
    "sg-1000",
    "snes",
    "vectrex",
    "videopac",
    "virtualboy",
    "wonderswan",
    "wonderswancolor",
    "zxspectrum",
}
keep_files = {"simple-dark.xml"}
temporary_path = destination_path + ".trimmed"

with zipfile.ZipFile(source_path, "r") as source:
    members = [member for member in source.infolist() if "/" in member.filename]
    if not members:
        raise SystemExit("Simple Dark archive has no codeload root directory")
    root = members[0].filename.split("/", 1)[0]
    prefix = root + "/"

    selected = []
    for member in source.infolist():
        if not member.filename.startswith(prefix):
            continue
        relative = member.filename[len(prefix):]
        if not relative:
            continue
        top = relative.split("/", 1)[0]
        if relative in keep_files or top in keep_dirs:
            selected.append(member)

    required = {"simple-dark.xml", *keep_dirs}
    present = set()
    for member in selected:
        relative = member.filename[len(prefix):]
        present.add(relative.split("/", 1)[0])
    missing = sorted(required - present)
    if missing:
        raise SystemExit("Simple Dark archive misses required webOS content: " + ", ".join(missing))

    with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as destination:
        for member in selected:
            if member.is_dir():
                destination.writestr(member.filename, b"")
            else:
                destination.writestr(member.filename, source.read(member.filename))

before = os.path.getsize(source_path)
after = os.path.getsize(temporary_path)
os.replace(temporary_path, destination_path)
print(f"Bundled Simple Dark archive: {before} -> {after} bytes ({before - after} bytes saved)")
PY
fi

"$CC" -Os -s "$repo_root/packaging/launch-emulationstation.c" -o "$package_dir/emulationstation"
sed "s/@VERSION@/$version/g" "$repo_root/packaging/appinfo.json.in" > "$package_dir/appinfo.json"
rsvg-convert -w 160 -h 160 "$repo_root/packaging/icon.svg" -o "$package_dir/icon160.png"

vcpkg_lib="$vcpkg_root/installed/$triplet/lib"
search_roots=(
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
      printf '  searched: %s\n' "${search_roots[@]}" >&2
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
du -sh "$package_dir/resources" "$package_dir/lib" "$package_dir" || true

(
  cd "$dist_dir"
  ares-package package
)
ipk="$(find "$dist_dir" -maxdepth 1 -name '*.ipk' -print -quit)"
[[ -n "$ipk" ]] || { echo "ares-package did not produce an IPK." >&2; exit 1; }

if [[ -n "${WEBOS_BUILD_SUFFIX:-}" ]]; then
  renamed="$dist_dir/com.rf1705.emulationstation_${version}-${WEBOS_BUILD_SUFFIX}_arm.ipk"
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