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

# RetroArch's webOS port handles the real LG Magic Remote Back button via the
# dedicated SDL-webOS scancode. Some webOS/SDL combinations expose the same
# button through SDL's standard AC_BACK key/scancode instead, so accept both.
# Numeric 0 remains a normal key and is deliberately not a Back fallback.
include_anchor = "#include <SDL.h>\n"
include_addition = "#ifdef WEBOS\n#include <SDL_webOS.h>\n#endif\n"
if "#include <SDL_webOS.h>" not in text:
    if include_anchor not in text:
        raise SystemExit("SDL include anchor not found")
    text = text.replace(include_anchor, include_anchor + include_addition, 1)

replacements = {
    "mappedKey == SDLK_0 || mappedKey == 403 || mappedKey == 461":
        "ev.key.keysym.scancode == SDL_WEBOS_SCANCODE_BACK || ev.key.keysym.scancode == SDL_SCANCODE_AC_BACK || mappedKey == SDLK_AC_BACK || mappedKey == 461",
    # Numeric 1/2 are known to reach EmulationStation on the tested Magic Remote.
    # Keep the proper webOS colour scancodes as optional equivalents for TVs that expose them.
    "mappedKey == SDLK_1 || mappedKey == 404":
        "mappedKey == SDLK_1 || ev.key.keysym.scancode == SDL_WEBOS_SCANCODE_GREEN",
    "mappedKey == SDLK_2 || mappedKey == 405":
        "mappedKey == SDLK_2 || ev.key.keysym.scancode == SDL_WEBOS_SCANCODE_YELLOW",
}

for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f"remote key mapping anchor not found: {old}")
    text = text.replace(old, new)

# Log the raw SDL values. If a particular TV still does not expose Back through
# either semantic path, /tmp/com.rf1705.emulationstation.log will tell us the
# exact keysym/scancode instead of requiring another guess.
keydown_anchor = "\t\tint mappedKey = ev.key.keysym.sym;\n#ifdef WEBOS\n"
keydown_log = (
    "\t\tint mappedKey = ev.key.keysym.sym;\n#ifdef WEBOS\n"
    "\t\tLOG(LogInfo) << \"webOS key down: sym=\" << (int)ev.key.keysym.sym\n"
    "\t\t\t<< \" scancode=\" << (int)ev.key.keysym.scancode << \" repeat=\" << (int)ev.key.repeat;\n"
)
if keydown_anchor not in text:
    raise SystemExit("webOS keydown logging anchor not found")
text = text.replace(keydown_anchor, keydown_log, 1)

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
print("Applied native and standard SDL webOS Back handling plus Magic Remote logging")
