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

# Log every SDL event before InputManager dispatches it. Back is known not to
# arrive as SDL_KEYDOWN on the tested TV, so this lets us see whether SDL emits
# a window, mouse, user or other event instead. These entries go to the normal
# EmulationStation log below <home>/.emulationstation/es_log.txt.
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

# Keep detailed key logging as well so ordinary remote buttons give us their
# exact keysym/scancode and make the event sequence easy to correlate.
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

# RetroArch does not consume its SDL queue strictly in chronological order on
# webOS. It pumps SDL, then pulls keyboard/input events from a type range before
# its video driver consumes SDL_WINDOWEVENTs. This matters for the LG Back key:
# the compositor may also generate FOCUS_LOST (SDL_WINDOWEVENT 13) at the same
# time. Give EmulationStation the same key-first behavior so the native Back
# scancode can be handled before a pending focus event.
main_path = source_root / "es-app/src/main.cpp"
if not main_path.is_file():
    raise SystemExit(f"missing upstream file: {main_path}")

main_text = main_path.read_text()
poll_call = "SDL_PollEvent(&event)"
poll_call_count = main_text.count(poll_call)
if poll_call_count != 2:
    raise SystemExit(f"expected 2 SDL_PollEvent calls in main loop, found {poll_call_count}")
main_text = main_text.replace(poll_call, "pollEmulationStationEvent(&event)")

main_anchor = "int main(int argc, char* argv[])\n{\n"
poll_helper = (
    "static int pollEmulationStationEvent(SDL_Event* event)\n"
    "{\n"
    "#ifdef WEBOS\n"
    "\tSDL_PumpEvents();\n"
    "\tint result = SDL_PeepEvents(event, 1, SDL_GETEVENT, SDL_KEYDOWN, SDL_KEYUP);\n"
    "\tif(result > 0)\n"
    "\t\treturn result;\n"
    "#endif\n"
    "\treturn SDL_PollEvent(event);\n"
    "}\n\n"
)
if main_anchor not in main_text:
    raise SystemExit("main function anchor not found")
main_text = main_text.replace(main_anchor, poll_helper + main_anchor, 1)
main_path.write_text(main_text)

print("Applied webOS Back handling, key-first SDL polling, remote mappings and full SDL event diagnostics")
