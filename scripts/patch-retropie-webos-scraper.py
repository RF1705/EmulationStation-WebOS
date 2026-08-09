#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch-retropie-webos-scraper.py <RetroPie EmulationStation source>")

root = Path(sys.argv[1]).resolve()
settings_cpp = root / "es-core/src/Settings.cpp"
gui_menu_cpp = root / "es-app/src/guis/GuiMenu.cpp"
screenscraper_cpp = root / "es-app/src/scrapers/ScreenScraper.cpp"

for path in (settings_cpp, gui_menu_cpp, screenscraper_cpp):
    if not path.is_file():
        raise SystemExit(f"missing upstream file: {path}")

# Persist ScreenScraper language/region preferences. German language and the
# European metadata region are the sensible defaults for this webOS port;
# ScreenScraper still falls back to English/world data when localized metadata
# is unavailable.
text = settings_cpp.read_text()
anchor = '\tmStringMap["WebOSLanguage"] = "de";\n'
addition = '\tmStringMap["WebOSScraperLanguage"] = "de";\n\tmStringMap["WebOSScraperRegion"] = "eu";\n'
if 'WebOSScraperLanguage' not in text:
    if anchor not in text:
        raise SystemExit("could not find webOS language settings anchor")
    text = text.replace(anchor, anchor + addition, 1)

# Prefer ScreenScraper for new webOS installations. Existing users keep their
# saved choice from es_settings.cfg.
old_default = '\tmStringMap["Scraper"] = "TheGamesDB";\n'
new_default = '#ifdef WEBOS\n\tmStringMap["Scraper"] = "ScreenScraper";\n#else\n\tmStringMap["Scraper"] = "TheGamesDB";\n#endif\n'
if old_default in text:
    text = text.replace(old_default, new_default, 1)
settings_cpp.write_text(text)

# Add language and region selectors directly to the existing scraper settings.
text = gui_menu_cpp.read_text()
anchor = '\ts->addSaveFunc([scraper_list] { Settings::getInstance()->setString("Scraper", scraper_list->getSelected()); });\n'
ui = r'''

#ifdef WEBOS
	auto scraper_language = std::make_shared<OptionListComponent<std::string>>(mWindow,
		webosTr("SCRAPER LANGUAGE", "SCRAPER-SPRACHE"), false);
	const std::string currentLanguage = Settings::getInstance()->getString("WebOSScraperLanguage");
	scraper_language->add("Deutsch", "de", currentLanguage == "de" || currentLanguage.empty());
	scraper_language->add("English", "en", currentLanguage == "en");
	scraper_language->add("Français", "fr", currentLanguage == "fr");
	scraper_language->add("Español", "es", currentLanguage == "es");
	scraper_language->add("Italiano", "it", currentLanguage == "it");
	scraper_language->add("Nederlands", "nl", currentLanguage == "nl");
	scraper_language->add("Português", "pt", currentLanguage == "pt");
	scraper_language->add("Polski", "pl", currentLanguage == "pl");
	s->addWithLabel(webosTr("LANGUAGE (SCREENSCRAPER)", "SPRACHE (SCREENSCRAPER)"), scraper_language);
	s->addSaveFunc([scraper_language] {
		Settings::getInstance()->setString("WebOSScraperLanguage", scraper_language->getSelected());
	});

	auto scraper_region = std::make_shared<OptionListComponent<std::string>>(mWindow,
		webosTr("SCRAPER REGION", "SCRAPER-REGION"), false);
	const std::string currentRegion = Settings::getInstance()->getString("WebOSScraperRegion");
	scraper_region->add(webosTr("Europe", "Europa"), "eu", currentRegion == "eu" || currentRegion.empty());
	scraper_region->add("USA", "us", currentRegion == "us");
	scraper_region->add(webosTr("Japan", "Japan"), "jp", currentRegion == "jp");
	scraper_region->add(webosTr("World", "Welt"), "wor", currentRegion == "wor");
	s->addWithLabel(webosTr("REGION (SCREENSCRAPER)", "REGION (SCREENSCRAPER)"), scraper_region);
	s->addSaveFunc([scraper_region] {
		Settings::getInstance()->setString("WebOSScraperRegion", scraper_region->getSelected());
	});
#endif
'''
if 'WebOSScraperLanguage' not in text:
    if anchor not in text:
        raise SystemExit("could not find scraper settings UI anchor")
    text = text.replace(anchor, anchor + ui, 1)
gui_menu_cpp.write_text(text)

# RetroPie hardcodes ScreenScraper to EN/US. Override every local config object
# with the user's webOS preferences. The existing parser already has English and
# world fallbacks when a selected language/region is missing.
text = screenscraper_cpp.read_text()
needle = '\tScreenScraperRequest::ScreenScraperConfig ssConfig;\n'
replacement = r'''	ScreenScraperRequest::ScreenScraperConfig ssConfig;
#ifdef WEBOS
	{
		const std::string language = Settings::getInstance()->getString("WebOSScraperLanguage");
		const std::string region = Settings::getInstance()->getString("WebOSScraperRegion");
		if(!language.empty())
			ssConfig.language = language;
		if(!region.empty())
			ssConfig.region = region;
	}
#endif
'''
count = text.count(needle)
if count == 0:
    raise SystemExit("could not find ScreenScraper config objects")
text = text.replace(needle, replacement)
screenscraper_cpp.write_text(text)

print(f"Applied webOS ScreenScraper language/region patch ({count} config sites)")
