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

build_bluez() {
  local version=5.83
  local archive="$download_dir/bluez-$version.tar.xz"
  local source="$source_root/bluez-$version"
  if [[ -s "$prefix/lib/pkgconfig/bluez.pc" || -s "$prefix/lib/libbluetooth.so" ]]; then
    return
  fi
  fetch "https://www.kernel.org/pub/linux/bluetooth/bluez-$version.tar.xz" "$archive"
  rm -rf "$source"
  tar -xJf "$archive" -C "$source_root"
  (
    cd "$source"
    ./configure \
      --host="$target" \
      --prefix="$prefix" \
      --enable-library \
      --enable-shared \
      --disable-static \
      --disable-systemd \
      --disable-udev \
      --disable-cups \
      --disable-obex \
      --disable-mesh \
      --disable-tools \
      --disable-monitor \
      --disable-client \
      --disable-testing \
      --disable-manpages
    make -j"$jobs"
    make install
  )
}

build_alsa
build_bluez

echo "System dependencies installed below $prefix"
