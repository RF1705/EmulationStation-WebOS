#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch-retropie-webos-no-dummy.py <RetroPie EmulationStation source>")

root = Path(sys.argv[1]).resolve()
main_cpp = root / "es-app/src/main.cpp"
system_data_cpp = root / "es-app/src/SystemData.cpp"
gui_menu_cpp = root / "es-app/src/guis/GuiMenu.cpp"

for path in (main_cpp, system_data_cpp, gui_menu_cpp):
    if not path.is_file():
        raise SystemExit(f"missing upstream file: {path}")

# Ignore the legacy visible webOS bootstrap system from older installs. This
# makes upgrades clean immediately; the next save from Games & Systems writes
# a config without that entry at all.
text = system_data_cpp.read_text()
anchor = '\tname = system.child("name").text().get();\n'
addition = '''\tname = system.child("name").text().get();
#ifdef WEBOS
\tif(name == "webos")
\t{
\t\tLOG(LogInfo) << "Ignoring legacy webOS setup system";
\t\treturn nullptr;
\t}
#endif
'''
if "Ignoring legacy webOS setup system" not in text:
    if anchor not in text:
        raise SystemExit("SystemData webOS dummy anchor not found")
    text = text.replace(anchor, addition, 1)
system_data_cpp.write_text(text)

# The graphical system manager used to always write a visible webOS setup
# pseudo-console. HOME now opens the menu directly, so only real systems belong
# in es_systems.cfg.
text = gui_menu_cpp.read_text()
bootstrap = '''\t// Keep a tiny setup entry so a typo or an empty game directory can never
\t// lock the user out of EmulationStation's graphical configuration again.
\tpugi::xml_node bootstrap = list.append_child("system");
\tbootstrap.append_child("name").text().set("webos");
\tbootstrap.append_child("fullname").text().set(webosTr("Setup", "Einrichtung"));
\tbootstrap.append_child("path").text().set((Utils::FileSystem::getHomePath() + "/.emulationstation/bootstrap").c_str());
\tbootstrap.append_child("extension").text().set(".webos");
\tbootstrap.append_child("command").text().set("/bin/true");
\tbootstrap.append_child("platform").text().set("ignore");
\tbootstrap.append_child("theme").text().set("webos");

'''
if bootstrap in text:
    text = text.replace(bootstrap, "", 1)
elif 'bootstrap.append_child("name").text().set("webos")' in text:
    raise SystemExit("webOS bootstrap block changed unexpectedly")
gui_menu_cpp.write_text(text)

# Upstream treats an empty system vector as fatal. On webOS an empty library is
# a valid first-run state: keep ES alive and open GuiMenu so Games & Systems can
# be configured without a fake console entry.
text = main_cpp.read_text()
include_anchor = '#include "guis/GuiMsgBox.h"\n'
if '#include "guis/GuiMenu.h"' not in text:
    if include_anchor not in text:
        raise SystemExit("GuiMenu include anchor not found")
    text = text.replace(include_anchor, include_anchor + '#include "guis/GuiMenu.h"\n', 1)

empty_anchor = '''\tif(SystemData::sSystemVector.size() == 0)
\t{
\t\tLOG(LogError) << "No systems found! Does at least one system have a game present? (check that extensions match!)\\n(Also, make sure you've updated your es_systems.cfg for XML!)";
\t\t*errorString = "WE CAN'T FIND ANY SYSTEMS!\\n"
\t\t\t"CHECK THAT YOUR PATHS ARE CORRECT IN THE SYSTEMS CONFIGURATION FILE, "
\t\t\t"AND YOUR GAME DIRECTORY HAS AT LEAST ONE GAME WITH THE CORRECT EXTENSION.\\n\\n"
\t\t\t"VISIT EMULATIONSTATION.ORG FOR MORE INFORMATION.";
\t\treturn false;
\t}
'''
empty_replacement = '''\tif(SystemData::sSystemVector.size() == 0)
\t{
#ifdef WEBOS
\t\tLOG(LogInfo) << "No game systems found; opening webOS setup menu";
\t\treturn true;
#else
\t\tLOG(LogError) << "No systems found! Does at least one system have a game present? (check that extensions match!)\\n(Also, make sure you've updated your es_systems.cfg for XML!)";
\t\t*errorString = "WE CAN'T FIND ANY SYSTEMS!\\n"
\t\t\t"CHECK THAT YOUR PATHS ARE CORRECT IN THE SYSTEMS CONFIGURATION FILE, "
\t\t\t"AND YOUR GAME DIRECTORY HAS AT LEAST ONE GAME WITH THE CORRECT EXTENSION.\\n\\n"
\t\t\t"VISIT EMULATIONSTATION.ORG FOR MORE INFORMATION.";
\t\treturn false;
#endif
\t}
'''
if "No game systems found; opening webOS setup menu" not in text:
    if empty_anchor not in text:
        raise SystemExit("empty system startup anchor not found")
    text = text.replace(empty_anchor, empty_replacement, 1)

startup_anchor = '''\tif(errorMsg == NULL)
\t{
\t\tif(Utils::FileSystem::exists(InputManager::getConfigPath()) && InputManager::getInstance()->getNumConfiguredDevices() > 0)
\t\t{
\t\t\tViewController::get()->goToStart();
\t\t}else{
\t\t\twindow.pushGui(new GuiDetectDevice(&window, true, [] { ViewController::get()->goToStart(); }));
\t\t}
\t}
'''
startup_replacement = '''\tif(errorMsg == NULL)
\t{
#ifdef WEBOS
\t\tif(SystemData::sSystemVector.empty())
\t\t{
\t\t\tauto openSetupMenu = [&window] { window.pushGui(new GuiMenu(&window)); };
\t\t\tif(Utils::FileSystem::exists(InputManager::getConfigPath()) && InputManager::getInstance()->getNumConfiguredDevices() > 0)
\t\t\t\topenSetupMenu();
\t\t\telse
\t\t\t\twindow.pushGui(new GuiDetectDevice(&window, true, openSetupMenu));
\t\t}
\t\telse
#endif
\t\tif(Utils::FileSystem::exists(InputManager::getConfigPath()) && InputManager::getInstance()->getNumConfiguredDevices() > 0)
\t\t{
\t\t\tViewController::get()->goToStart();
\t\t}else{
\t\t\twindow.pushGui(new GuiDetectDevice(&window, true, [] { ViewController::get()->goToStart(); }));
\t\t}
\t}
'''
if "auto openSetupMenu = [&window]" not in text:
    if startup_anchor not in text:
        raise SystemExit("webOS first-run setup anchor not found")
    text = text.replace(startup_anchor, startup_replacement, 1)

main_cpp.write_text(text)
print("Removed webOS dummy system and enabled empty-library setup mode")
