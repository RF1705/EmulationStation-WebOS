#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch-retropie-webos-quit.py <RetroPie EmulationStation source>")

root = Path(sys.argv[1]).resolve()
gui_menu_cpp = root / "es-app/src/guis/GuiMenu.cpp"
system_view_cpp = root / "es-app/src/views/SystemView.cpp"

for path in (gui_menu_cpp, system_view_cpp):
    if not path.is_file():
        raise SystemExit(f"missing upstream file: {path}")

# Make RetroPie's desktop/Raspberry Pi quit menu appropriate for a TV app.
# Keep the EmulationStation restart/quit actions, but never offer rebooting or
# shutting down the whole webOS TV from inside the frontend.
text = gui_menu_cpp.read_text()

confirm_anchor = '\tbool confirm_quit = Settings::getInstance()->getBool("ConfirmQuit");\n'
confirm_replacement = (
    '#ifdef WEBOS\n'
    '\t// A TV remote can trigger quit very easily, so always confirm it.\n'
    '\tbool confirm_quit = true;\n'
    '#else\n'
    + confirm_anchor +
    '#endif\n'
)
if confirm_anchor not in text:
    raise SystemExit("GuiMenu ConfirmQuit anchor not found")
text = text.replace(confirm_anchor, confirm_replacement, 1)

# The webOS launcher historically starts ES with --no-exit. Do not let that
# desktop-oriented switch hide the explicit application quit action on TV.
show_exit_anchor = '\t\tif(Settings::getInstance()->getBool("ShowExit"))\n'
show_exit_replacement = (
    '#ifdef WEBOS\n'
    '\t\tif(true)\n'
    '#else\n'
    + show_exit_anchor +
    '#endif\n'
)
if show_exit_anchor not in text:
    raise SystemExit("GuiMenu ShowExit anchor not found")
text = text.replace(show_exit_anchor, show_exit_replacement, 1)

reboot_anchor = '\tauto static reboot_sys_fx = [] {\n'
push_anchor = '\tmWindow->pushGui(s);\n}\n\nvoid GuiMenu::addVersionInfo()\n'
if reboot_anchor not in text:
    raise SystemExit("GuiMenu system reboot anchor not found")
if push_anchor not in text:
    raise SystemExit("GuiMenu quit menu end anchor not found")
text = text.replace(reboot_anchor, '#ifndef WEBOS\n' + reboot_anchor, 1)
text = text.replace(push_anchor, '#endif\n\n' + push_anchor, 1)

gui_menu_cpp.write_text(text)

# Back/B already means "go back" everywhere below the system carousel. At the
# top-level SystemView there is nowhere further back to go, so on webOS turn it
# into the natural application-exit gesture and require an explicit YES.
text = system_view_cpp.read_text()

include_anchor = '#include "Window.h"\n'
include_addition = '#include "platform.h"\n#include "WebOSLocalization.h"\n'
if '#include "WebOSLocalization.h"' not in text:
    if include_anchor not in text:
        raise SystemExit("SystemView include anchor not found")
    text = text.replace(include_anchor, include_anchor + include_addition, 1)

switch_anchor = '\t\tswitch (mCarousel.type)\n'
quit_block = r'''#ifdef WEBOS
		if(config->isMappedTo("b", input))
		{
			auto quit_es_fx = [] {
				Scripting::fireEvent("quit");
				quitES();
			};

			mWindow->pushGui(new GuiMsgBox(
				mWindow,
				webosTr("REALLY QUIT EMULATIONSTATION?", "EMULATIONSTATION WIRKLICH BEENDEN?"),
				webosTr("YES", "JA"), quit_es_fx,
				webosTr("NO", "NEIN"), nullptr));
			return true;
		}
#endif

'''
if 'EMULATIONSTATION WIRKLICH BEENDEN?' not in text:
    if switch_anchor not in text:
        raise SystemExit("SystemView input switch anchor not found")
    text = text.replace(switch_anchor, quit_block + switch_anchor, 1)

system_view_cpp.write_text(text)

print("Applied TV-friendly webOS quit menu and top-level Back confirmation")
