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
print("Applied verified LG Magic Remote colour keycodes and switch scoping")
