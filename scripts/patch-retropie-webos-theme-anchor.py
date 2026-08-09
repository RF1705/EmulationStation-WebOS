#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 3 or sys.argv[2] not in ("prepare", "restore"):
    raise SystemExit("usage: patch-retropie-webos-theme-anchor.py <source> prepare|restore")

path = Path(sys.argv[1]).resolve() / "es-app/src/guis/GuiMenu.cpp"
if not path.is_file():
    raise SystemExit(f"missing upstream file: {path}")

text = path.read_text()
plain = 'GuiMenu::GuiMenu(Window* window) : GuiComponent(window), mMenu(window, "MAIN MENU"), mVersion(window)'
localized = 'GuiMenu::GuiMenu(Window* window) : GuiComponent(window), mMenu(window, webosTr("MAIN MENU", "HAUPTMENÜ")), mVersion(window)'

if sys.argv[2] == "prepare":
    if localized not in text:
        raise SystemExit("localized GuiMenu constructor not found")
    text = text.replace(localized, plain, 1)
else:
    if plain not in text:
        raise SystemExit("plain GuiMenu constructor not found")
    text = text.replace(plain, localized, 1)

path.write_text(text)
print(f"Theme patch constructor anchor: {sys.argv[2]}")
