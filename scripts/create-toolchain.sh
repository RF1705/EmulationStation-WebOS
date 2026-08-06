#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output="${WEBOS_CHAINLOAD_TOOLCHAIN:-$repo_root/build/webos-chainload.cmake}"
for variable in CC CXX AR RANLIB STRIP STAGING_DIR; do
  [[ -n "${!variable:-}" ]] || { echo "$variable is not set; source the webOS SDK environment first." >&2; exit 1; }
done
mkdir -p "$(dirname "$output")"
escape_sed() { printf '%s' "$1" | sed -e 's/[\/&]/\\&/g'; }
sed \
  -e "s/@CC@/$(escape_sed "$CC")/g" \
  -e "s/@CXX@/$(escape_sed "$CXX")/g" \
  -e "s/@AR@/$(escape_sed "$AR")/g" \
  -e "s/@RANLIB@/$(escape_sed "$RANLIB")/g" \
  -e "s/@STRIP@/$(escape_sed "$STRIP")/g" \
  -e "s/@SYSROOT@/$(escape_sed "$STAGING_DIR")/g" \
  -e "s/@CFLAGS@/$(escape_sed "${CFLAGS:-}")/g" \
  -e "s/@CXXFLAGS@/$(escape_sed "${CXXFLAGS:-}")/g" \
  -e "s/@LDFLAGS@/$(escape_sed "${LDFLAGS:-}")/g" \
  "$repo_root/cmake/webos-chainload.cmake.in" > "$output"
echo "WEBOS_CHAINLOAD_TOOLCHAIN=$output"
