#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
prefix="${WEBOS_DEPS_PREFIX:-$repo_root/build/webos-deps}"
source_root="${WEBOS_DEPS_SOURCE_DIR:-$repo_root/build/dependency-sources}"
download_dir="$source_root/downloads"
target="${WEBOS_HOST_TRIPLET:-arm-webos-linux-gnueabi}"
jobs="${JOBS:-$(getconf _NPROCESSORS_ONLN)}"

if [[ -z "${CC:-}" || -z "${STAGING_DIR:-}" ]]; then
  echo "Source the webOS SDK environment before building dependencies." >&2
  exit 1
fi

mkdir -p "$prefix" "$download_dir"

fetch() {
  local url="$1"
  local output="$2"
  if [[ ! -s "$output" ]]; then
    curl --fail --location --retry 3 "$url" --output "$output"
  fi
}

build_alsa() {
  local version=1.2.14
  local archive="$download_dir/alsa-lib-$version.tar.bz2"
  local source="$source_root/alsa-lib-$version"
  if [[ -s "$prefix/lib/pkgconfig/alsa.pc" ]]; then
    return
  fi
  fetch "https://www.alsa-project.org/files/pub/lib/alsa-lib-$version.tar.bz2" "$archive"
  rm -rf "$source"
  tar -xjf "$archive" -C "$source_root"
  (
    cd "$source"
    ./configure \
      --host="$target" \
      --prefix="$prefix" \
      --enable-shared \
      --disable-static \
      --disable-python \
      --disable-aload \
      --disable-topology
    make -j"$jobs"
    make install
  )
}

# webOS owns the Bluetooth stack and SDL-webOS exposes paired controllers.
# Building BlueZ here would only add an unused D-Bus dependency to the app.
build_alsa

echo "System dependencies installed below $prefix"
