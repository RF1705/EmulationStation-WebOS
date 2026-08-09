#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch-retropie-webos-remote.py <RetroPie EmulationStation source>")

path = Path(sys.argv[1]).resolve() / "es-core/src/InputManager.cpp"
if not path.is_file():
    raise SystemExit(f"missing upstream file: {path}")

text = path.read_text()

# Use the dedicated SDL-webOS remote scancodes. RetroArch handles the real LG
# Back button this way as well; the normal SDL keycode is not reliable on webOS.
include_anchor = "#include <SDL.h>\n"
include_addition = "#ifdef WEBOS\n#include <SDL_webOS.h>\n#endif\n"
if "#include <SDL_webOS.h>" not in text:
    if include_anchor not in text:
        raise SystemExit("SDL include anchor not found")
    text = text.replace(include_anchor, include_anchor + include_addition, 1)

replacements = {
    # Back is the native LG Back button. Red remains an optional alternate, but
    # the old numeric 0 fallback is intentionally removed.
    "mappedKey == SDLK_0 || mappedKey == 403 || mappedKey == 461":
        "ev.key.keysym.scancode == SDL_WEBOS_SCANCODE_BACK || ev.key.keysym.scancode == SDL_WEBOS_SCANCODE_RED || mappedKey == 461",
    # Numeric 1/2 are known to reach EmulationStation on the tested Magic Remote.
    # Also recognize the proper SDL-webOS colour scancodes when a TV exposes them.
    "mappedKey == SDLK_1 || mappedKey == 404":
        "mappedKey == SDLK_1 || ev.key.keysym.scancode == SDL_WEBOS_SCANCODE_GREEN",
    "mappedKey == SDLK_2 || mappedKey == 405":
        "mappedKey == SDLK_2 || ev.key.keysym.scancode == SDL_WEBOS_SCANCODE_YELLOW",
}

for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f"remote key mapping anchor not found: {old}")
    text = text.replace(old, new)

# mappedKey is a local variable inside SDL_KEYDOWN. Give that switch case its
# own scope so jumping to subsequent case labels is valid C++. Match only the
# case labels themselves so this does not depend on upstream tabs/spaces.
text, opened = re.subn(
    r"(?m)^(\s*)case SDL_KEYDOWN:\s*$",
    r"\1case SDL_KEYDOWN:\n\1{",
    text,
    count=1,
)
if opened != 1:
    raise SystemExit("SDL_KEYDOWN case label not found")

text, closed = re.subn(
    r"(?m)^(\s*)case SDL_KEYUP:\s*$",
    r"\1}\n\n\1case SDL_KEYUP:",
    text,
    count=1,
)
if closed != 1:
    raise SystemExit("SDL_KEYUP case label not found")

path.write_text(text)
print("Applied native SDL-webOS Back handling and Magic Remote mappings")
