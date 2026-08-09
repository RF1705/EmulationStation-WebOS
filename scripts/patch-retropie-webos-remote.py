#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch-retropie-webos-remote.py <RetroPie EmulationStation source>")

source_root = Path(sys.argv[1]).resolve()
path = source_root / "es-core/src/InputManager.cpp"
if not path.is_file():
    raise SystemExit(f"missing upstream file: {path}")

text = path.read_text()

# SDL-webOS delivers the LG Back button through its dedicated scancode once the
# application claims the key with SDL_WEBOS_ACCESS_POLICY_KEYS_BACK=true.
# Keep standard AC_BACK/keycode fallbacks as harmless compatibility paths.
include_anchor = "#include <SDL.h>\n"
include_addition = "#ifdef WEBOS\n#include <SDL_webOS.h>\n#endif\n"
if "#include <SDL_webOS.h>" not in text:
    if include_anchor not in text:
        raise SystemExit("SDL include anchor not found")
    text = text.replace(include_anchor, include_anchor + include_addition, 1)

replacements = {
    "mappedKey == SDLK_0 || mappedKey == 403 || mappedKey == 461":
        "ev.key.keysym.scancode == SDL_WEBOS_SCANCODE_BACK || ev.key.keysym.scancode == SDL_SCANCODE_AC_BACK || mappedKey == SDLK_AC_BACK || mappedKey == 461",
    # Map the standard SDL Menu key from the Magic Remote to EmulationStation's
    # Start action (F1). Keep numeric 1 / green as fallback shortcuts.
    "mappedKey == SDLK_1 || mappedKey == 404":
        "mappedKey == SDLK_1 || ev.key.keysym.scancode == SDL_WEBOS_SCANCODE_GREEN || ev.key.keysym.scancode == SDL_SCANCODE_MENU",
    "mappedKey == SDLK_2 || mappedKey == 405":
        "mappedKey == SDLK_2 || ev.key.keysym.scancode == SDL_WEBOS_SCANCODE_YELLOW",
}

for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f"remote key mapping anchor not found: {old}")
    text = text.replace(old, new)

# Keep full SDL diagnostics for now so the first build with the access-policy
# hint proves that Back arrives as a real keyboard event.
parse_anchor = (
    "bool InputManager::parseEvent(const SDL_Event& ev, Window* window)\n"
    "{\n"
    "\tbool causedEvent = false;\n"
)
parse_log = (
    "bool InputManager::parseEvent(const SDL_Event& ev, Window* window)\n"
    "{\n"
    "\tbool causedEvent = false;\n"
    "#ifdef WEBOS\n"
    "\tLOG(LogInfo) << \"webOS SDL event: type=\" << (unsigned int)ev.type;\n"
    "\tif(ev.type == SDL_WINDOWEVENT)\n"
    "\t\tLOG(LogInfo) << \"webOS window event: event=\" << (int)ev.window.event\n"
    "\t\t\t<< \" data1=\" << ev.window.data1 << \" data2=\" << ev.window.data2;\n"
    "\telse if(ev.type == SDL_MOUSEBUTTONDOWN || ev.type == SDL_MOUSEBUTTONUP)\n"
    "\t\tLOG(LogInfo) << \"webOS mouse button: button=\" << (int)ev.button.button\n"
    "\t\t\t<< \" state=\" << (int)ev.button.state << \" x=\" << ev.button.x << \" y=\" << ev.button.y;\n"
    "\telse if(ev.type == SDL_MOUSEWHEEL)\n"
    "\t\tLOG(LogInfo) << \"webOS mouse wheel: x=\" << ev.wheel.x << \" y=\" << ev.wheel.y\n"
    "\t\t\t<< \" direction=\" << (int)ev.wheel.direction;\n"
    "\telse if(ev.type >= SDL_USEREVENT)\n"
    "\t\tLOG(LogInfo) << \"webOS user event: type=\" << (unsigned int)ev.type\n"
    "\t\t\t<< \" code=\" << ev.user.code << \" data1=\" << ev.user.data1 << \" data2=\" << ev.user.data2;\n"
    "#endif\n"
)
if parse_anchor not in text:
    raise SystemExit("parseEvent logging anchor not found")
text = text.replace(parse_anchor, parse_log, 1)

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
# own scope so jumping to subsequent case labels is valid C++.
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
print("Applied webOS Back handling, Menu mapping, remote mappings and SDL event diagnostics")
