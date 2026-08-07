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

path.write_text(text)
print("Applied verified LG Magic Remote colour keycodes")
