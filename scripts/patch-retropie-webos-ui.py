#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch-retropie-webos-ui.py <RetroPie EmulationStation source>")

root = Path(sys.argv[1]).resolve()
gui_menu_cpp = root / "es-app/src/guis/GuiMenu.cpp"
gui_menu_h = root / "es-app/src/guis/GuiMenu.h"
gui_settings_cpp = root / "es-app/src/guis/GuiSettings.cpp"
settings_cpp = root / "es-core/src/Settings.cpp"
localization_h = root / "es-core/src/WebOSLocalization.h"

for path in (gui_menu_cpp, gui_menu_h, gui_settings_cpp, settings_cpp):
    if not path.is_file():
        raise SystemExit(f"missing upstream file: {path}")

localization_h.write_text(r'''#pragma once
#ifndef ES_CORE_WEBOS_LOCALIZATION_H
#define ES_CORE_WEBOS_LOCALIZATION_H

#include "Settings.h"
#include <string>

inline bool webosGerman()
{
#ifdef WEBOS
    return Settings::getInstance()->getString("WebOSLanguage") != "en";
#else
    return false;
#endif
}

inline const char* webosTr(const char* english, const char* german)
{
    return webosGerman() ? german : english;
}

inline std::string webosTrString(const char* english, const char* german)
{
    return std::string(webosTr(english, german));
}

#endif
''')

# Persist webOS-specific UI and library settings using EmulationStation's normal
# settings file. German is the default for this webOS port but can be changed in
# the UI without pulling in gettext/ICU.
text = settings_cpp.read_text()
anchor = '\tmStringMap["StartupSystem"] = "";\n'
addition = r'''	#ifdef WEBOS
	mStringMap["WebOSLanguage"] = "de";
	mBoolMap["WebOSSystemScummVM"] = false;
	mBoolMap["WebOSSystemNES"] = false;
	mBoolMap["WebOSSystemSNES"] = false;
	mBoolMap["WebOSSystemMegaDrive"] = false;
	mBoolMap["WebOSSystemMasterSystem"] = false;
	mBoolMap["WebOSSystemGB"] = false;
	mBoolMap["WebOSSystemGBC"] = false;
	mBoolMap["WebOSSystemGBA"] = false;
	mBoolMap["WebOSSystemPSX"] = false;
	mStringMap["WebOSPathScummVM"] = "/media/developer/network-storage/games/ScummVM";
	mStringMap["WebOSPathNES"] = "/media/developer/network-storage/games/NES";
	mStringMap["WebOSPathSNES"] = "/media/developer/network-storage/games/SNES";
	mStringMap["WebOSPathMegaDrive"] = "/media/developer/network-storage/games/Mega Drive";
	mStringMap["WebOSPathMasterSystem"] = "/media/developer/network-storage/games/Master System";
	mStringMap["WebOSPathGB"] = "/media/developer/network-storage/games/Game Boy";
	mStringMap["WebOSPathGBC"] = "/media/developer/network-storage/games/Game Boy Color";
	mStringMap["WebOSPathGBA"] = "/media/developer/network-storage/games/Game Boy Advance";
	mStringMap["WebOSPathPSX"] = "/media/developer/network-storage/games/PlayStation";
	#endif
'''
if addition not in text:
    if anchor not in text:
        raise SystemExit("could not find Settings defaults anchor")
    text = text.replace(anchor, anchor + addition, 1)
settings_cpp.write_text(text)

# Add the webOS library setup entry point to GuiMenu.
text = gui_menu_h.read_text()
h_anchor = '\tvoid openUISettings();\n'
if '\tvoid openWebOSGameSettings();\n' not in text:
    if h_anchor not in text:
        raise SystemExit("could not find GuiMenu declaration anchor")
    text = text.replace(h_anchor, h_anchor + '\tvoid openWebOSGameSettings();\n', 1)
gui_menu_h.write_text(text)

text = gui_menu_cpp.read_text()
include_anchor = '#include "guis/GuiSettings.h"\n'
include_addition = '''#include "guis/GuiTextEditPopup.h"\n#include "utils/FileSystemUtil.h"\n#include "WebOSLocalization.h"\n#include <pugixml.hpp>\n'''
if '#include "WebOSLocalization.h"' not in text:
    if include_anchor not in text:
        raise SystemExit("could not find GuiMenu include anchor")
    text = text.replace(include_anchor, include_anchor + include_addition, 1)

# Small built-in catalogue. Paths remain freely editable in the UI; these are
# only useful defaults. Launcher commands deliberately remain harmless until
# the separate webOS emulator handoff is configured.
constructor_anchor = 'GuiMenu::GuiMenu(Window* window) : GuiComponent(window), mMenu(window, "MAIN MENU"), mVersion(window)\n'
helpers = r'''#ifdef WEBOS
struct WebOSSystemPreset
{
	const char* enabledKey;
	const char* pathKey;
	const char* name;
	const char* fullName;
	const char* extensions;
	const char* platform;
	const char* theme;
};

static const WebOSSystemPreset sWebOSSystemPresets[] = {
	{"WebOSSystemScummVM", "WebOSPathScummVM", "scummvm", "ScummVM", ".svm .scummvm", "scummvm", "scummvm"},
	{"WebOSSystemNES", "WebOSPathNES", "nes", "Nintendo Entertainment System", ".7z .fds .nes .zip", "nes", "nes"},
	{"WebOSSystemSNES", "WebOSPathSNES", "snes", "Super Nintendo", ".7z .bin .fig .mgd .sfc .smc .swc .zip", "snes", "snes"},
	{"WebOSSystemMegaDrive", "WebOSPathMegaDrive", "megadrive", "Sega Mega Drive", ".7z .bin .gen .md .sg .smd .zip", "genesis", "megadrive"},
	{"WebOSSystemMasterSystem", "WebOSPathMasterSystem", "mastersystem", "Sega Master System", ".7z .bin .sms .zip", "mastersystem", "mastersystem"},
	{"WebOSSystemGB", "WebOSPathGB", "gb", "Game Boy", ".7z .gb .zip", "gb", "gb"},
	{"WebOSSystemGBC", "WebOSPathGBC", "gbc", "Game Boy Color", ".7z .gbc .zip", "gbc", "gbc"},
	{"WebOSSystemGBA", "WebOSPathGBA", "gba", "Game Boy Advance", ".7z .gba .zip", "gba", "gba"},
	{"WebOSSystemPSX", "WebOSPathPSX", "psx", "PlayStation", ".bin .cbn .chd .cue .img .iso .m3u .mdf .pbp .toc .z .znx", "psx", "psx"}
};

static bool saveWebOSSystemsConfig()
{
	pugi::xml_document doc;
	pugi::xml_node list = doc.append_child("systemList");

	// Keep a tiny setup entry so a typo or an empty game directory can never
	// lock the user out of EmulationStation's graphical configuration again.
	pugi::xml_node bootstrap = list.append_child("system");
	bootstrap.append_child("name").text().set("webos");
	bootstrap.append_child("fullname").text().set(webosTr("Setup", "Einrichtung"));
	bootstrap.append_child("path").text().set((Utils::FileSystem::getHomePath() + "/.emulationstation/bootstrap").c_str());
	bootstrap.append_child("extension").text().set(".webos");
	bootstrap.append_child("command").text().set("/bin/true");
	bootstrap.append_child("platform").text().set("ignore");
	bootstrap.append_child("theme").text().set("webos");

	Settings* settings = Settings::getInstance();
	for(const auto& preset : sWebOSSystemPresets)
	{
		if(!settings->getBool(preset.enabledKey))
			continue;

		const std::string path = settings->getString(preset.pathKey);
		if(path.empty())
			continue;

		pugi::xml_node system = list.append_child("system");
		system.append_child("name").text().set(preset.name);
		system.append_child("fullname").text().set(preset.fullName);
		system.append_child("path").text().set(path.c_str());
		system.append_child("extension").text().set(preset.extensions);
		system.append_child("command").text().set("/bin/true");
		system.append_child("platform").text().set(preset.platform);
		system.append_child("theme").text().set(preset.theme);
	}

	const std::string configPath = SystemData::getConfigPath(true);
	Utils::FileSystem::createDirectory(Utils::FileSystem::getParent(configPath));
	return doc.save_file(configPath.c_str(), "  ");
}
#endif

'''
if '#ifdef WEBOS\nstruct WebOSSystemPreset' not in text:
    if constructor_anchor not in text:
        raise SystemExit("could not find GuiMenu constructor anchor")
    text = text.replace(constructor_anchor, helpers + constructor_anchor, 1)

# Localize the main menu title and expose the library manager before the normal
# RetroPie settings entries.
text = text.replace(
    'GuiMenu::GuiMenu(Window* window) : GuiComponent(window), mMenu(window, "MAIN MENU"), mVersion(window)',
    'GuiMenu::GuiMenu(Window* window) : GuiComponent(window), mMenu(window, webosTr("MAIN MENU", "HAUPTMENÜ")), mVersion(window)',
    1,
)
menu_anchor = '\tif (isFullUI) {\n\t\taddEntry("SCRAPER", 0x777777FF, true, [this] { openScraperSettings(); });\n'
menu_replacement = '\tif (isFullUI) {\n#ifdef WEBOS\n\t\taddEntry(webosTr("GAMES & SYSTEMS", "SPIELE & SYSTEME"), 0x777777FF, true, [this] { openWebOSGameSettings(); });\n#endif\n\t\taddEntry(webosTr("SCRAPER", "SPIELINFORMATIONEN"), 0x777777FF, true, [this] { openScraperSettings(); });\n'
if menu_anchor in text:
    text = text.replace(menu_anchor, menu_replacement, 1)
elif 'openWebOSGameSettings()' not in text:
    raise SystemExit("could not find GuiMenu main menu anchor")

# Translate the most visible built-in menu entries and settings labels. The
# setting values themselves are deliberately not translated.
translations = {
    '"SOUND SETTINGS"': 'webosTr("SOUND SETTINGS", "TONEINSTELLUNGEN")',
    '"UI SETTINGS"': 'webosTr("UI SETTINGS", "OBERFLÄCHE")',
    '"GAME COLLECTION SETTINGS"': 'webosTr("GAME COLLECTION SETTINGS", "SPIELESAMMLUNGEN")',
    '"OTHER SETTINGS"': 'webosTr("OTHER SETTINGS", "WEITERE EINSTELLUNGEN")',
    '"CONFIGURE INPUT"': 'webosTr("CONFIGURE INPUT", "STEUERUNG EINRICHTEN")',
    '"QUIT"': 'webosTr("QUIT", "BEENDEN")',
    '"SCRAPE FROM"': 'webosTr("SCRAPE FROM", "DATENQUELLE")',
    '"SCRAPE RATINGS"': 'webosTr("SCRAPE RATINGS", "BEWERTUNGEN LADEN")',
    '"SCRAPE NOW"': 'webosTr("SCRAPE NOW", "JETZT LADEN")',
    '"SYSTEM VOLUME"': 'webosTr("SYSTEM VOLUME", "SYSTEMLAUTSTÄRKE")',
    '"ENABLE NAVIGATION SOUNDS"': 'webosTr("ENABLE NAVIGATION SOUNDS", "NAVIGATIONSTÖNE")',
    '"ENABLE VIDEO AUDIO"': 'webosTr("ENABLE VIDEO AUDIO", "VIDEO-TON")',
    '"UI MODE"': 'webosTr("UI MODE", "UI-MODUS")',
    '"SCREENSAVER SETTINGS"': 'webosTr("SCREENSAVER SETTINGS", "BILDSCHIRMSCHONER")',
    '"QUICK SYSTEM SELECT"': 'webosTr("QUICK SYSTEM SELECT", "SCHNELLER SYSTEMWECHSEL")',
    '"TRANSITION STYLE"': 'webosTr("TRANSITION STYLE", "ÜBERGANG")',
    '"THEME SET"': 'webosTr("THEME SET", "DESIGN")',
    '"SHOW HELP PROMPTS"': 'webosTr("SHOW HELP PROMPTS", "TASTENHINWEISE ANZEIGEN")',
    '"ON-SCREEN HELP"': 'webosTr("ON-SCREEN HELP", "TASTENHINWEISE")',
}
for old, new in translations.items():
    text = text.replace(old, new)

# Language selector at the top of UI settings.
ui_anchor = 'void GuiMenu::openUISettings()\n{\n\tauto s = new GuiSettings(mWindow, webosTr("UI SETTINGS", "OBERFLÄCHE"));\n'
ui_addition = r'''void GuiMenu::openUISettings()
{
	auto s = new GuiSettings(mWindow, webosTr("UI SETTINGS", "OBERFLÄCHE"));

#ifdef WEBOS
	auto language = std::make_shared<OptionListComponent<std::string>>(mWindow, webosTr("LANGUAGE", "SPRACHE"), false);
	language->add("Deutsch", "de", Settings::getInstance()->getString("WebOSLanguage") != "en");
	language->add("English", "en", Settings::getInstance()->getString("WebOSLanguage") == "en");
	s->addWithLabel(webosTr("LANGUAGE", "SPRACHE"), language);
	s->addSaveFunc([language] { Settings::getInstance()->setString("WebOSLanguage", language->getSelected()); });
#endif
'''
if ui_anchor in text:
    text = text.replace(ui_anchor, ui_addition, 1)
elif 'WebOSLanguage' not in text:
    raise SystemExit("could not find UI settings anchor")

# Insert the webOS graphical system manager before the sound settings function.
sound_anchor = 'void GuiMenu::openSoundSettings()\n'
manager = r'''#ifdef WEBOS
void GuiMenu::openWebOSGameSettings()
{
	auto s = new GuiSettings(mWindow, webosTr("GAMES & SYSTEMS", "SPIELE & SYSTEME"));
	Settings* settings = Settings::getInstance();

	auto info = std::make_shared<TextComponent>(mWindow,
		webosTr("Enable a system and set its game folder. Changes are saved when you go back; restart EmulationStation to rescan games.",
			"System aktivieren und Spieleordner setzen. Beim Zurückgehen wird gespeichert; danach EmulationStation neu starten."),
		Font::get(FONT_SIZE_SMALL), 0x777777FF);
	ComponentListRow infoRow;
	infoRow.addElement(info, true);
	s->addRow(infoRow);

	for(const auto& preset : sWebOSSystemPresets)
	{
		auto enabled = std::make_shared<SwitchComponent>(mWindow);
		enabled->setState(settings->getBool(preset.enabledKey));
		s->addWithLabel(preset.fullName, enabled);

		const std::string pathKey = preset.pathKey;
		const std::string enabledKey = preset.enabledKey;
		auto pathText = std::make_shared<TextComponent>(mWindow, settings->getString(pathKey), Font::get(FONT_SIZE_SMALL), 0x777777FF);
		ComponentListRow pathRow;
		pathRow.addElement(std::make_shared<TextComponent>(mWindow, webosTr("GAME FOLDER", "SPIELEORDNER"), Font::get(FONT_SIZE_MEDIUM), 0x777777FF), true);
		pathRow.addElement(pathText, false);
		pathRow.addElement(makeArrow(mWindow), false);
		pathRow.makeAcceptInputHandler([this, pathText, pathKey, preset] {
			const std::string current = Settings::getInstance()->getString(pathKey);
			mWindow->pushGui(new GuiTextEditPopup(mWindow,
				preset.fullName,
				current,
				[pathText, pathKey](const std::string& value) {
					Settings::getInstance()->setString(pathKey, value);
					pathText->setText(value);
				}, false));
		});
		s->addRow(pathRow);

		s->addSaveFunc([enabled, enabledKey] {
			Settings::getInstance()->setBool(enabledKey, enabled->getState());
		});
	}

	s->addSaveFunc([this] {
		if(!saveWebOSSystemsConfig())
		{
			mWindow->pushGui(new GuiMsgBox(mWindow,
				webosTr("Could not save the systems configuration.", "Systemkonfiguration konnte nicht gespeichert werden."),
				"OK"));
		}
	});

	mWindow->pushGui(s);
}
#endif

'''
if manager not in text:
    if sound_anchor not in text:
        raise SystemExit("could not find sound settings function anchor")
    text = text.replace(sound_anchor, manager + sound_anchor, 1)

gui_menu_cpp.write_text(text)

# Localize the generic settings Back button and help prompt too, so nested
# settings dialogs do not immediately fall back to English.
text = gui_settings_cpp.read_text()
settings_include_anchor = '#include "Settings.h"\n'
if '#include "WebOSLocalization.h"' not in text:
    if settings_include_anchor not in text:
        raise SystemExit("could not find GuiSettings include anchor")
    text = text.replace(settings_include_anchor, settings_include_anchor + '#include "WebOSLocalization.h"\n', 1)
text = text.replace('mMenu.addButton("BACK", "go back", [this] { delete this; });',
                    'mMenu.addButton(webosTr("BACK", "ZURÜCK"), webosTr("go back", "zurück"), [this] { delete this; });')
text = text.replace('HelpPrompt("b", "back")', 'HelpPrompt("b", webosTr("back", "zurück"))')
text = text.replace('HelpPrompt("start", "close")', 'HelpPrompt("start", webosTr("close", "schließen"))')
gui_settings_cpp.write_text(text)

print("Applied graphical webOS library setup and German/English localization")
