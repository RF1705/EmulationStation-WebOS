#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch-retropie-webos-remote.py <RetroPie EmulationStation source>")

path = Path(sys.argv[1]).resolve() / "es-core/src/InputManager.cpp"
if not path.is_file():
    raise SystemExit(f"missing upstream file: {path}")

text = path.read_text()
replacements = {
    "mappedKey == SDLK_0 || mappedKey == 403 || mappedKey == 461":
        "mappedKey == SDLK_0 || mappedKey == 0x18e || mappedKey == 0x1008ffa3 || mappedKey == 461",
    "mappedKey == SDLK_1 || mappedKey == 404":
        "mappedKey == SDLK_1 || mappedKey == 0x18f || mappedKey == 0x1008ffa4",
    "mappedKey == SDLK_2 || mappedKey == 405":
        "mappedKey == SDLK_2 || mappedKey == 0x190 || mappedKey == 0x1008ffa5",
}

for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f"remote key mapping anchor not found: {old}")
    text = text.replace(old, new)

# The webOS mapping declares mappedKey inside the SDL_KEYDOWN switch case.
# Give that case its own scope so C++ can legally jump to later case labels.
keydown_start = "\tcase SDL_KEYDOWN:\n\t\tint mappedKey = ev.key.keysym.sym;\n"
keydown_scoped = "\tcase SDL_KEYDOWN:\n\t{\n\t\tint mappedKey = ev.key.keysym.sym;\n"
if keydown_start not in text:
    raise SystemExit("SDL_KEYDOWN scope anchor not found")
text = text.replace(keydown_start, keydown_scoped, 1)

keyup_anchor = "\t\treturn true;\n\n\tcase SDL_KEYUP:\n\t{\n"
keyup_scoped = "\t\treturn true;\n\t}\n\n\tcase SDL_KEYUP:\n\t{\n"
if keyup_anchor not in text:
    raise SystemExit("SDL_KEYUP scope anchor not found")
text = text.replace(keyup_anchor, keyup_scoped, 1)

path.write_text(text)
print("Applied verified LG Magic Remote colour keycodes and switch scoping")
