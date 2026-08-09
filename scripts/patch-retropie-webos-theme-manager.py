#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch-retropie-webos-theme-manager.py <RetroPie EmulationStation source>")

root = Path(sys.argv[1]).resolve()
cmake = root / "CMakeLists.txt"
gui_menu_h = root / "es-app/src/guis/GuiMenu.h"
gui_menu_cpp = root / "es-app/src/guis/GuiMenu.cpp"

for path in (cmake, gui_menu_h, gui_menu_cpp):
    if not path.is_file():
        raise SystemExit(f"missing upstream file: {path}")

# libzip is used only by the webOS theme downloader. libcurl is already a
# normal EmulationStation dependency and is already linked into the frontend.
text = cmake.read_text()
find_anchor = "find_package(RapidJSON REQUIRED)\n"
find_addition = "# webOS downloadable theme archives\nif(WEBOS)\n    find_package(libzip CONFIG REQUIRED)\nendif()\n"
if "find_package(libzip CONFIG REQUIRED)" not in text:
    if find_anchor not in text:
        raise SystemExit("libzip find_package anchor not found")
    text = text.replace(find_anchor, find_anchor + find_addition, 1)

libs_anchor = "    nanosvg\n)\n"
libs_addition = "\nif(WEBOS)\n    LIST(APPEND COMMON_LIBRARIES libzip::zip)\nendif()\n"
if "libzip::zip" not in text:
    if libs_anchor not in text:
        raise SystemExit("COMMON_LIBRARIES anchor not found")
    text = text.replace(libs_anchor, libs_anchor + libs_addition, 1)
cmake.write_text(text)

text = gui_menu_h.read_text()
h_anchor = "\tvoid openWebOSGameSettings();\n"
if "\tvoid openWebOSThemeManager();\n" not in text:
    if h_anchor not in text:
        raise SystemExit("webOS GuiMenu declaration anchor not found")
    text = text.replace(h_anchor, h_anchor + "\tvoid openWebOSThemeManager();\n", 1)
gui_menu_h.write_text(text)

text = gui_menu_cpp.read_text()
include_anchor = '#include "WebOSLocalization.h"\n'
include_addition = r'''#ifdef WEBOS
#include <curl/curl.h>
#include <zip.h>
#include <cstdio>
#endif
'''
if "#include <zip.h>" not in text:
    if include_anchor not in text:
        raise SystemExit("webOS localization include anchor not found")
    text = text.replace(include_anchor, include_anchor + include_addition, 1)

constructor_anchor = "GuiMenu::GuiMenu(Window* window) : GuiComponent(window), mMenu(window, \"MAIN MENU\"), mVersion(window)\n"
helpers = r'''#ifdef WEBOS
struct WebOSThemeEntry
{
	const char* displayName;
	const char* folderName;
	const char* archiveUrl;
};

// Pin theme archives to known upstream commits. Themes are downloaded only on
// explicit user request and remain in ~/.emulationstation/themes across IPK updates.
static const WebOSThemeEntry sWebOSThemes[] = {
	{"Carbon", "carbon", "https://codeload.github.com/RetroPie/es-theme-carbon/zip/b09973e0b0c589cb11fe772c169a6ff5d588b390"},
	{"Simple", "simple", "https://codeload.github.com/RetroPie/es-theme-simple/zip/5a6c1daf965b9d410398243c232a34911dad8826"},
	{"Simple Dark", "simple-dark", "https://codeload.github.com/RetroPie/es-theme-simple-dark/zip/058472cfbc3b4fe9ddf1ab452908fab40e32d29c"},
};

static bool webosThemeInstalled(const WebOSThemeEntry& theme)
{
	return Utils::FileSystem::isDirectory(Utils::FileSystem::getHomePath() +
		"/.emulationstation/themes/" + theme.folderName);
}

static bool webosDownloadFile(const std::string& url, const std::string& path, std::string& error)
{
	FILE* output = fopen(path.c_str(), "wb");
	if(!output)
	{
		error = webosTr("Could not create temporary download file.", "Temporäre Download-Datei konnte nicht erstellt werden.");
		return false;
	}

	CURL* curl = curl_easy_init();
	if(!curl)
	{
		fclose(output);
		error = webosTr("Could not initialize downloader.", "Downloader konnte nicht initialisiert werden.");
		return false;
	}

	curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
	curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
	curl_easy_setopt(curl, CURLOPT_FAILONERROR, 1L);
	curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L);
	curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 20L);
	curl_easy_setopt(curl, CURLOPT_TIMEOUT, 180L);
	curl_easy_setopt(curl, CURLOPT_USERAGENT, "EmulationStation-webOS/1.0");
	curl_easy_setopt(curl, CURLOPT_WRITEDATA, output);

	const CURLcode result = curl_easy_perform(curl);
	curl_easy_cleanup(curl);
	fclose(output);

	if(result != CURLE_OK)
	{
		Utils::FileSystem::removeFile(path);
		error = std::string(webosTr("Download failed: ", "Download fehlgeschlagen: ")) + curl_easy_strerror(result);
		return false;
	}

	return true;
}

static bool webosSafeArchivePath(const std::string& path)
{
	if(path.empty() || path[0] == '/' || path.find('\\') != std::string::npos)
		return false;

	size_t start = 0;
	while(start <= path.size())
	{
		const size_t slash = path.find('/', start);
		const std::string part = path.substr(start, slash == std::string::npos ? std::string::npos : slash - start);
		if(part == "..")
			return false;
		if(slash == std::string::npos)
			break;
		start = slash + 1;
	}
	return true;
}

static bool webosExtractTheme(const std::string& archivePath, const WebOSThemeEntry& theme, std::string& error)
{
	int zipError = 0;
	zip_t* archive = zip_open(archivePath.c_str(), ZIP_RDONLY, &zipError);
	if(!archive)
	{
		error = webosTr("Theme archive could not be opened.", "Theme-Archiv konnte nicht geöffnet werden.");
		return false;
	}

	const std::string themeRoot = Utils::FileSystem::getHomePath() + "/.emulationstation/themes";
	const std::string destinationRoot = themeRoot + "/" + theme.folderName;
	if(!Utils::FileSystem::createDirectory(destinationRoot))
	{
		zip_close(archive);
		error = webosTr("Theme directory could not be created.", "Theme-Verzeichnis konnte nicht erstellt werden.");
		return false;
	}

	const zip_int64_t entries = zip_get_num_entries(archive, 0);
	zip_uint64_t totalSize = 0;
	const zip_uint64_t maxEntrySize = 128ULL * 1024ULL * 1024ULL;
	const zip_uint64_t maxTotalSize = 512ULL * 1024ULL * 1024ULL;

	for(zip_uint64_t i = 0; i < (zip_uint64_t)entries; ++i)
	{
		const char* rawName = zip_get_name(archive, i, ZIP_FL_ENC_GUESS);
		if(!rawName)
			continue;

		const std::string archiveName(rawName);
		const size_t firstSlash = archiveName.find('/');
		if(firstSlash == std::string::npos)
			continue;

		const std::string relative = archiveName.substr(firstSlash + 1);
		if(relative.empty())
			continue;
		if(!webosSafeArchivePath(relative))
		{
			zip_close(archive);
			error = webosTr("Unsafe path in theme archive.", "Unsicherer Pfad im Theme-Archiv.");
			return false;
		}

		const std::string destination = destinationRoot + "/" + relative;
		if(relative.back() == '/')
		{
			if(!Utils::FileSystem::createDirectory(destination))
			{
				zip_close(archive);
				error = webosTr("Could not create theme directory.", "Theme-Verzeichnis konnte nicht erstellt werden.");
				return false;
			}
			continue;
		}

		zip_stat_t stat;
		zip_stat_init(&stat);
		if(zip_stat_index(archive, i, 0, &stat) != 0 || stat.size > maxEntrySize)
		{
			zip_close(archive);
			error = webosTr("Theme archive contains an invalid or oversized file.", "Theme-Archiv enthält eine ungültige oder zu große Datei.");
			return false;
		}
		totalSize += stat.size;
		if(totalSize > maxTotalSize)
		{
			zip_close(archive);
			error = webosTr("Theme archive is too large.", "Theme-Archiv ist zu groß.");
			return false;
		}

		if(!Utils::FileSystem::createDirectory(Utils::FileSystem::getParent(destination)))
		{
			zip_close(archive);
			error = webosTr("Could not create theme directory.", "Theme-Verzeichnis konnte nicht erstellt werden.");
			return false;
		}

		zip_file_t* input = zip_fopen_index(archive, i, 0);
		if(!input)
		{
			zip_close(archive);
			error = webosTr("Could not read a file from the theme archive.", "Datei im Theme-Archiv konnte nicht gelesen werden.");
			return false;
		}

		FILE* output = fopen(destination.c_str(), "wb");
		if(!output)
		{
			zip_fclose(input);
			zip_close(archive);
			error = webosTr("Could not write a theme file.", "Theme-Datei konnte nicht geschrieben werden.");
			return false;
		}

		char buffer[32768];
		zip_int64_t bytes = 0;
		bool writeOk = true;
		while((bytes = zip_fread(input, buffer, sizeof(buffer))) > 0)
		{
			if(fwrite(buffer, 1, (size_t)bytes, output) != (size_t)bytes)
			{
				writeOk = false;
				break;
			}
		}
		if(bytes < 0)
			writeOk = false;

		fclose(output);
		zip_fclose(input);

		if(!writeOk)
		{
			zip_close(archive);
			error = webosTr("Could not extract the complete theme.", "Theme konnte nicht vollständig entpackt werden.");
			return false;
		}
	}

	zip_close(archive);
	return true;
}

static bool webosInstallTheme(const WebOSThemeEntry& theme, std::string& error)
{
	const std::string configRoot = Utils::FileSystem::getHomePath() + "/.emulationstation";
	if(!Utils::FileSystem::createDirectory(configRoot + "/themes"))
	{
		error = webosTr("Theme directory could not be created.", "Theme-Verzeichnis konnte nicht erstellt werden.");
		return false;
	}

	const std::string archivePath = configRoot + "/theme-download.zip";
	if(!webosDownloadFile(theme.archiveUrl, archivePath, error))
		return false;

	const bool extracted = webosExtractTheme(archivePath, theme, error);
	Utils::FileSystem::removeFile(archivePath);
	return extracted;
}
#endif

'''
if "struct WebOSThemeEntry" not in text:
    if constructor_anchor not in text:
        raise SystemExit("GuiMenu constructor anchor not found")
    text = text.replace(constructor_anchor, helpers + constructor_anchor, 1)

# Add the downloader entry just before the existing theme selector. This means
# downloaded themes are managed from the same UI area where they are selected.
theme_anchor = "\t// theme set\n"
theme_row = r'''#ifdef WEBOS
	ComponentListRow themeDownloadRow;
	themeDownloadRow.addElement(std::make_shared<TextComponent>(mWindow,
		webosTr("DOWNLOAD THEMES", "THEMES HERUNTERLADEN"), Font::get(FONT_SIZE_MEDIUM), 0x777777FF), true);
	themeDownloadRow.addElement(makeArrow(mWindow), false);
	themeDownloadRow.makeAcceptInputHandler(std::bind(&GuiMenu::openWebOSThemeManager, this));
	s->addRow(themeDownloadRow);
#endif

'''
if "DOWNLOAD THEMES" not in text:
    if theme_anchor not in text:
        raise SystemExit("theme selector anchor not found")
    text = text.replace(theme_anchor, theme_row + theme_anchor, 1)

method_anchor = "void GuiMenu::openOtherSettings()\n"
method = r'''#ifdef WEBOS
void GuiMenu::openWebOSThemeManager()
{
	auto s = new GuiSettings(mWindow, webosTr("DOWNLOAD THEMES", "THEMES HERUNTERLADEN"));

	ComponentListRow infoRow;
	infoRow.addElement(std::make_shared<TextComponent>(mWindow,
		webosTr("Themes are downloaded from the official RetroPie repositories and remain installed after app updates.",
			"Themes werden aus den offiziellen RetroPie-Repositories geladen und bleiben auch nach App-Updates installiert."),
		Font::get(FONT_SIZE_SMALL), 0x777777FF), true);
	s->addRow(infoRow);

	for(const auto& theme : sWebOSThemes)
	{
		const bool installed = webosThemeInstalled(theme);
		std::string label = theme.displayName;
		if(installed)
			label += webosTr(" (installed)", " (installiert)");

		ComponentListRow row;
		row.addElement(std::make_shared<TextComponent>(mWindow, label, Font::get(FONT_SIZE_MEDIUM), 0x777777FF), true);
		row.addElement(makeArrow(mWindow), false);
		row.makeAcceptInputHandler([this, theme] {
			std::string error;
			LOG(LogInfo) << "webOS theme manager: downloading " << theme.displayName;
			if(!webosInstallTheme(theme, error))
			{
				mWindow->pushGui(new GuiMsgBox(mWindow,
					std::string(webosTr("Theme installation failed.\n\n", "Theme-Installation fehlgeschlagen.\n\n")) + error));
				return;
			}

			mWindow->pushGui(new GuiMsgBox(mWindow,
				std::string(theme.displayName) + webosTr(" was installed.\nApply this theme now?", " wurde installiert.\nDieses Theme jetzt anwenden?"),
				webosTr("YES", "JA"), [theme] {
					const std::string oldTheme = Settings::getInstance()->getString("ThemeSet");
					Settings::getInstance()->setString("ThemeSet", theme.folderName);
					Settings::getInstance()->saveFile();
					Scripting::fireEvent("theme-changed", theme.folderName, oldTheme);
					CollectionSystemManager::get()->updateSystemsList();
					ViewController::get()->reloadAll(true);
				}, webosTr("NO", "NEIN"), nullptr));
		});
		s->addRow(row);
	}

	mWindow->pushGui(s);
}
#endif

'''
if "void GuiMenu::openWebOSThemeManager()" not in text:
    if method_anchor not in text:
        raise SystemExit("theme manager method anchor not found")
    text = text.replace(method_anchor, method + method_anchor, 1)

gui_menu_cpp.write_text(text)
print("Applied downloadable webOS theme manager")
