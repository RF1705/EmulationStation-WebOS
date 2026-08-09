#include "guis/GuiMenu.h"

#include "components/OptionListComponent.h"
#include "components/SliderComponent.h"
#include "components/SwitchComponent.h"
#include "guis/GuiCollectionSystemsOptions.h"
#include "guis/GuiDetectDevice.h"
#include "guis/GuiGeneralScreensaverOptions.h"
#include "guis/GuiMsgBox.h"
#include "guis/GuiScraperStart.h"
#include "guis/GuiSettings.h"
#include "guis/GuiTextEditPopup.h"
#include "utils/FileSystemUtil.h"
#include "WebOSLocalization.h"
#ifdef WEBOS
#include <curl/curl.h>
#include <zip.h>
#include <cstdio>
#endif
#include <pugixml.hpp>
#include "views/UIModeController.h"
#include "views/ViewController.h"
#include "CollectionSystemManager.h"
#include "EmulationStation.h"
#include "Scripting.h"
#include "SystemData.h"
#include "VolumeControl.h"
#include <SDL_events.h>
#include <algorithm>
#include "platform.h"
#include "FileSorts.h"
#include "views/gamelist/IGameListView.h"
#include "guis/GuiInfoPopup.h"

#ifdef WEBOS
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

static std::string webosNearestDirectory(std::string path)
{
	while(!path.empty() && !Utils::FileSystem::isDirectory(path))
	{
		const std::string parent = Utils::FileSystem::getParent(path);
		if(parent.empty() || parent == path)
			break;
		path = parent;
	}

	if(Utils::FileSystem::isDirectory(path))
		return path;

	const char* fallbacks[] = {
		"/media/developer/network-storage/games",
		"/media/developer/network-storage",
		"/media/developer",
		"/media",
		"/"
	};
	for(const char* fallback : fallbacks)
		if(Utils::FileSystem::isDirectory(fallback))
			return fallback;

	return "/";
}

class GuiDirectoryBrowser : public GuiComponent
{
public:
	typedef std::function<void(const std::string&)> SelectCallback;

	GuiDirectoryBrowser(Window* window, const std::string& initialPath, const SelectCallback& callback) :
		GuiComponent(window), mPath(webosNearestDirectory(initialPath)), mCallback(callback)
	{
		rebuild();
	}

	bool input(InputConfig* config, Input input) override
	{
		if(config->isMappedTo("b", input) && input.value != 0)
		{
			delete this;
			return true;
		}
		return GuiComponent::input(config, input);
	}

	std::vector<HelpPrompt> getHelpPrompts() override
	{
		std::vector<HelpPrompt> prompts;
		prompts.push_back(HelpPrompt("a", webosTr("open", "öffnen")));
		prompts.push_back(HelpPrompt("b", webosTr("back", "zurück")));
		return prompts;
	}

private:
	void addDirectory(const std::string& label, const std::string& target)
	{
		ComponentListRow row;
		row.addElement(std::make_shared<TextComponent>(mWindow, label, Font::get(FONT_SIZE_MEDIUM), 0x777777FF), true);
		row.addElement(makeArrow(mWindow), false);
		row.makeAcceptInputHandler([this, target] {
			mPath = webosNearestDirectory(target);
			rebuild();
		});
		mMenu->addRow(row);
	}

	void rebuild()
	{
		if(mMenu)
		{
			removeChild(mMenu.get());
			mMenu.reset();
		}

		mMenu.reset(new MenuComponent(mWindow, webosTr("SELECT GAME FOLDER", "SPIELEORDNER WÄHLEN")));
		addChild(mMenu.get());

		ComponentListRow currentRow;
		currentRow.addElement(std::make_shared<TextComponent>(mWindow, mPath, Font::get(FONT_SIZE_SMALL), 0x777777FF), true);
		mMenu->addRow(currentRow);

		const std::string parent = Utils::FileSystem::getParent(mPath);
		if(!parent.empty() && parent != mPath)
			addDirectory("..", parent);

		std::vector<std::string> directories;
		for(const std::string& entry : Utils::FileSystem::getDirContent(mPath, false))
		{
			if(Utils::FileSystem::isDirectory(entry) && !Utils::FileSystem::isHidden(entry))
				directories.push_back(entry);
		}
		std::sort(directories.begin(), directories.end());

		for(const std::string& directory : directories)
			addDirectory(Utils::FileSystem::getFileName(directory), directory);

		mMenu->addButton(webosTr("SELECT THIS FOLDER", "DIESEN ORDNER WÄHLEN"),
			webosTr("use this directory", "diesen Ordner verwenden"), [this] {
				mCallback(mPath);
				delete this;
			});

		setSize((float)Renderer::getScreenWidth(), (float)Renderer::getScreenHeight());
		mMenu->setPosition((mSize.x() - mMenu->getSize().x()) / 2, Renderer::getScreenHeight() * 0.08f);
	}

	std::unique_ptr<MenuComponent> mMenu;
	std::string mPath;
	SelectCallback mCallback;
};

static bool saveWebOSSystemsConfig()
{
	pugi::xml_document doc;
	pugi::xml_node list = doc.append_child("systemList");

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

#ifdef WEBOS
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
			continue;

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

		const std::string parentDirectory = Utils::FileSystem::getParent(destination);
		if(!Utils::FileSystem::createDirectory(parentDirectory))
		{
			zip_close(archive);
			error = std::string(webosTr("Could not create theme directory: ", "Theme-Verzeichnis konnte nicht erstellt werden: ")) + parentDirectory;
			LOG(LogError) << "webOS theme manager: mkdir failed: " << parentDirectory;
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
	const std::string themesRoot = configRoot + "/themes";
	if(!Utils::FileSystem::createDirectory(themesRoot))
	{
		error = std::string(webosTr("Theme directory could not be created: ", "Theme-Verzeichnis konnte nicht erstellt werden: ")) + themesRoot;
		LOG(LogError) << "webOS theme manager: mkdir failed: " << themesRoot;
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

GuiMenu::GuiMenu(Window* window) : GuiComponent(window), mMenu(window, webosTr("MAIN MENU", "HAUPTMENÜ")), mVersion(window)
{
	bool isFullUI = UIModeController::getInstance()->isUIModeFull();

	if (isFullUI) {
#ifdef WEBOS
		addEntry(webosTr("GAMES & SYSTEMS", "SPIELE & SYSTEME"), 0x777777FF, true, [this] { openWebOSGameSettings(); });
#endif
		addEntry(webosTr("SCRAPER", "SPIELINFORMATIONEN"), 0x777777FF, true, [this] { openScraperSettings(); });
		addEntry(webosTr("SOUND SETTINGS", "TONEINSTELLUNGEN"), 0x777777FF, true, [this] { openSoundSettings(); });
		addEntry(webosTr("UI SETTINGS", "OBERFLÄCHE"), 0x777777FF, true, [this] { openUISettings(); });
		addEntry(webosTr("GAME COLLECTION SETTINGS", "SPIELESAMMLUNGEN"), 0x777777FF, true, [this] { openCollectionSystemSettings(); });
		addEntry(webosTr("OTHER SETTINGS", "WEITERE EINSTELLUNGEN"), 0x777777FF, true, [this] { openOtherSettings(); });
		addEntry(webosTr("CONFIGURE INPUT", "STEUERUNG EINRICHTEN"), 0x777777FF, true, [this] { openConfigInput(); });
	} else {
		addEntry(webosTr("SOUND SETTINGS", "TONEINSTELLUNGEN"), 0x777777FF, true, [this] { openSoundSettings(); });
	}

	addEntry(webosTr("QUIT", "BEENDEN"), 0x777777FF, true, [this] {openQuitMenu(); });

	addChild(&mMenu);
	addVersionInfo();
	setSize(mMenu.getSize());
	setPosition((Renderer::getScreenWidth() - mSize.x()) / 2, Renderer::getScreenHeight() * 0.15f);
}

void GuiMenu::openScraperSettings()
{
	auto s = new GuiSettings(mWindow, "SCRAPER");

	// scrape from
	auto scraper_list = std::make_shared< OptionListComponent< std::string > >(mWindow, webosTr("SCRAPE FROM", "DATENQUELLE"), false);
	std::vector<std::string> scrapers = getScraperList();

	// Select either the first entry of the one read from the settings, just in case the scraper from settings has vanished.
	for(auto it = scrapers.cbegin(); it != scrapers.cend(); it++)
		scraper_list->add(*it, *it, *it == Settings::getInstance()->getString("Scraper"));

	s->addWithLabel(webosTr("SCRAPE FROM", "DATENQUELLE"), scraper_list);
	s->addSaveFunc([scraper_list] { Settings::getInstance()->setString("Scraper", scraper_list->getSelected()); });


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

	// scrape ratings
	auto scrape_ratings = std::make_shared<SwitchComponent>(mWindow);
	scrape_ratings->setState(Settings::getInstance()->getBool("ScrapeRatings"));
	s->addWithLabel(webosTr("SCRAPE RATINGS", "BEWERTUNGEN LADEN"), scrape_ratings);
	s->addSaveFunc([scrape_ratings] { Settings::getInstance()->setBool("ScrapeRatings", scrape_ratings->getState()); });

	// scrape now
	ComponentListRow row;
	auto openScrapeNow = [this] { mWindow->pushGui(new GuiScraperStart(mWindow)); };
	std::function<void()> openAndSave = openScrapeNow;
	openAndSave = [s, openAndSave] { s->save(); openAndSave(); };
	row.makeAcceptInputHandler(openAndSave);

	auto scrape_now = std::make_shared<TextComponent>(mWindow, webosTr("SCRAPE NOW", "JETZT LADEN"), Font::get(FONT_SIZE_MEDIUM), 0x777777FF);
	auto bracket = makeArrow(mWindow);
	row.addElement(scrape_now, true);
	row.addElement(bracket, false);
	s->addRow(row);

	mWindow->pushGui(s);
}

#ifdef WEBOS
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
		pathRow.makeAcceptInputHandler([this, pathText, pathKey] {
			const std::string current = Settings::getInstance()->getString(pathKey);
			mWindow->pushGui(new GuiDirectoryBrowser(mWindow, current,
				[pathText, pathKey](const std::string& value) {
					Settings::getInstance()->setString(pathKey, value);
					pathText->setText(value);
				}));
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

void GuiMenu::openSoundSettings()
{
	auto s = new GuiSettings(mWindow, webosTr("SOUND SETTINGS", "TONEINSTELLUNGEN"));

	// volume
	auto volume = std::make_shared<SliderComponent>(mWindow, 0.f, 100.f, 1.f, "%");
	volume->setValue((float)VolumeControl::getInstance()->getVolume());
	s->addWithLabel(webosTr("SYSTEM VOLUME", "SYSTEMLAUTSTÄRKE"), volume);
	s->addSaveFunc([volume] { VolumeControl::getInstance()->setVolume((int)Math::round(volume->getValue())); });

	if (UIModeController::getInstance()->isUIModeFull())
	{
#if defined(__linux__)
		// audio card
		auto audio_card = std::make_shared< OptionListComponent<std::string> >(mWindow, "AUDIO CARD", false);
		std::vector<std::string> audio_cards;
		audio_cards.push_back("default");
		audio_cards.push_back("sysdefault");
		audio_cards.push_back("dmix");
		audio_cards.push_back("hw");
		audio_cards.push_back("plughw");
		audio_cards.push_back("null");
		if (Settings::getInstance()->getString("AudioCard") != "") {
			if(std::find(audio_cards.begin(), audio_cards.end(), Settings::getInstance()->getString("AudioCard")) == audio_cards.end()) {
				audio_cards.push_back(Settings::getInstance()->getString("AudioCard"));
			}
		}
		for(auto ac = audio_cards.cbegin(); ac != audio_cards.cend(); ac++)
			audio_card->add(*ac, *ac, Settings::getInstance()->getString("AudioCard") == *ac);
		s->addWithLabel("AUDIO CARD", audio_card);
		s->addSaveFunc([audio_card] {
			Settings::getInstance()->setString("AudioCard", audio_card->getSelected());
			VolumeControl::getInstance()->deinit();
			VolumeControl::getInstance()->init();
		});

		// volume control device
		auto vol_dev = std::make_shared< OptionListComponent<std::string> >(mWindow, "AUDIO DEVICE", false);
		std::vector<std::string> transitions;
		transitions.push_back("PCM");
		transitions.push_back("HDMI");
		transitions.push_back("Headphone");
		transitions.push_back("Speaker");
		transitions.push_back("Master");
		transitions.push_back("Digital");
		transitions.push_back("Analogue");
		if (Settings::getInstance()->getString("AudioDevice") != "") {
			if(std::find(transitions.begin(), transitions.end(), Settings::getInstance()->getString("AudioDevice")) == transitions.end()) {
				transitions.push_back(Settings::getInstance()->getString("AudioDevice"));
			}
		}
		for(auto it = transitions.cbegin(); it != transitions.cend(); it++)
			vol_dev->add(*it, *it, Settings::getInstance()->getString("AudioDevice") == *it);
		s->addWithLabel("AUDIO DEVICE", vol_dev);
		s->addSaveFunc([vol_dev] {
			Settings::getInstance()->setString("AudioDevice", vol_dev->getSelected());
			VolumeControl::getInstance()->deinit();
			VolumeControl::getInstance()->init();
		});
#endif

		// disable sounds
		auto sounds_enabled = std::make_shared<SwitchComponent>(mWindow);
		sounds_enabled->setState(Settings::getInstance()->getBool("EnableSounds"));
		s->addWithLabel(webosTr("ENABLE NAVIGATION SOUNDS", "NAVIGATIONSTÖNE"), sounds_enabled);
		s->addSaveFunc([sounds_enabled] {
			if (sounds_enabled->getState()
				&& !Settings::getInstance()->getBool("EnableSounds")
				&& PowerSaver::getMode() == PowerSaver::INSTANT)
			{
				Settings::getInstance()->setString("PowerSaverMode", "default");
				PowerSaver::init();
			}
			Settings::getInstance()->setBool("EnableSounds", sounds_enabled->getState());
		});

		auto video_audio = std::make_shared<SwitchComponent>(mWindow);
		video_audio->setState(Settings::getInstance()->getBool("VideoAudio"));
		s->addWithLabel(webosTr("ENABLE VIDEO AUDIO", "VIDEO-TON"), video_audio);
		s->addSaveFunc([video_audio] { Settings::getInstance()->setBool("VideoAudio", video_audio->getState()); });

#ifdef _OMX_
		// OMX player Audio Device
		auto omx_audio_dev = std::make_shared< OptionListComponent<std::string> >(mWindow, "OMX PLAYER AUDIO DEVICE", false);
		std::vector<std::string> omx_cards;
		// RPi Specific  Audio Cards
		omx_cards.push_back("local");
		omx_cards.push_back("hdmi");
		omx_cards.push_back("both");
		omx_cards.push_back("alsa");
		omx_cards.push_back("alsa:hw:0,0");
		omx_cards.push_back("alsa:hw:1,0");
		if (Settings::getInstance()->getString("OMXAudioDev") != "") {
			if (std::find(omx_cards.begin(), omx_cards.end(), Settings::getInstance()->getString("OMXAudioDev")) == omx_cards.end()) {
				omx_cards.push_back(Settings::getInstance()->getString("OMXAudioDev"));
			}
		}
		for (auto it = omx_cards.cbegin(); it != omx_cards.cend(); it++)
			omx_audio_dev->add(*it, *it, Settings::getInstance()->getString("OMXAudioDev") == *it);
		s->addWithLabel("OMX PLAYER AUDIO DEVICE", omx_audio_dev);
		s->addSaveFunc([omx_audio_dev] {
			if (Settings::getInstance()->getString("OMXAudioDev") != omx_audio_dev->getSelected())
				Settings::getInstance()->setString("OMXAudioDev", omx_audio_dev->getSelected());
		});
#endif
	}

	mWindow->pushGui(s);

}

void GuiMenu::openUISettings()
{
	auto s = new GuiSettings(mWindow, webosTr("UI SETTINGS", "OBERFLÄCHE"));

#ifdef WEBOS
	auto language = std::make_shared<OptionListComponent<std::string>>(mWindow, webosTr("LANGUAGE", "SPRACHE"), false);
	language->add("Deutsch", "de", Settings::getInstance()->getString("WebOSLanguage") != "en");
	language->add("English", "en", Settings::getInstance()->getString("WebOSLanguage") == "en");
	s->addWithLabel(webosTr("LANGUAGE", "SPRACHE"), language);
	s->addSaveFunc([language] { Settings::getInstance()->setString("WebOSLanguage", language->getSelected()); });
#endif

	//UI mode
	auto UImodeSelection = std::make_shared< OptionListComponent<std::string> >(mWindow, webosTr("UI MODE", "UI-MODUS"), false);
	std::vector<std::string> UImodes = UIModeController::getInstance()->getUIModes();
	for (auto it = UImodes.cbegin(); it != UImodes.cend(); it++)
		UImodeSelection->add(*it, *it, Settings::getInstance()->getString("UIMode") == *it);
	s->addWithLabel(webosTr("UI MODE", "UI-MODUS"), UImodeSelection);
	Window* window = mWindow;
	s->addSaveFunc([ UImodeSelection, window]
	{
		std::string selectedMode = UImodeSelection->getSelected();
		if (selectedMode != "Full")
		{
			std::string msg = "You are changing the UI to a restricted mode:\n" + selectedMode + "\n";
			msg += "This will hide most menu-options to prevent changes to the system.\n";
			msg += "To unlock and return to the full UI, enter this code: \n";
			msg += "\"" + UIModeController::getInstance()->getFormattedPassKeyStr() + "\"\n\n";
			msg += "Do you want to proceed?";
			window->pushGui(new GuiMsgBox(window, msg,
				"YES", [selectedMode] {
					LOG(LogDebug) << "Setting UI mode to " << selectedMode;
					Settings::getInstance()->setString("UIMode", selectedMode);
					Settings::getInstance()->saveFile();
			}, "NO",nullptr));
		}
	});

	// screensaver
	ComponentListRow screensaver_row;
	screensaver_row.elements.clear();
	screensaver_row.addElement(std::make_shared<TextComponent>(mWindow, webosTr("SCREENSAVER SETTINGS", "BILDSCHIRMSCHONER"), Font::get(FONT_SIZE_MEDIUM), 0x777777FF), true);
	screensaver_row.addElement(makeArrow(mWindow), false);
	screensaver_row.makeAcceptInputHandler(std::bind(&GuiMenu::openScreensaverOptions, this));
	s->addRow(screensaver_row);

	// quick system select (left/right in game list view)
	auto quick_sys_select = std::make_shared<SwitchComponent>(mWindow);
	quick_sys_select->setState(Settings::getInstance()->getBool("QuickSystemSelect"));
	s->addWithLabel(webosTr("QUICK SYSTEM SELECT", "SCHNELLER SYSTEMWECHSEL"), quick_sys_select);
	s->addSaveFunc([quick_sys_select] { Settings::getInstance()->setBool("QuickSystemSelect", quick_sys_select->getState()); });

	// carousel transition option
	auto move_carousel = std::make_shared<SwitchComponent>(mWindow);
	move_carousel->setState(Settings::getInstance()->getBool("MoveCarousel"));
	s->addWithLabel("CAROUSEL TRANSITIONS", move_carousel);
	s->addSaveFunc([move_carousel] {
		if (move_carousel->getState()
			&& !Settings::getInstance()->getBool("MoveCarousel")
			&& PowerSaver::getMode() == PowerSaver::INSTANT)
		{
			Settings::getInstance()->setString("PowerSaverMode", "default");
			PowerSaver::init();
		}
		Settings::getInstance()->setBool("MoveCarousel", move_carousel->getState());
	});

	// transition style
	auto transition_style = std::make_shared< OptionListComponent<std::string> >(mWindow, webosTr("TRANSITION STYLE", "ÜBERGANG"), false);
	std::vector<std::string> transitions;
	transitions.push_back("fade");
	transitions.push_back("slide");
	transitions.push_back("instant");
	for(auto it = transitions.cbegin(); it != transitions.cend(); it++)
		transition_style->add(*it, *it, Settings::getInstance()->getString("TransitionStyle") == *it);
	s->addWithLabel(webosTr("TRANSITION STYLE", "ÜBERGANG"), transition_style);
	s->addSaveFunc([transition_style] {
		if (Settings::getInstance()->getString("TransitionStyle") == "instant"
			&& transition_style->getSelected() != "instant"
			&& PowerSaver::getMode() == PowerSaver::INSTANT)
		{
			Settings::getInstance()->setString("PowerSaverMode", "default");
			PowerSaver::init();
		}
		Settings::getInstance()->setString("TransitionStyle", transition_style->getSelected());
	});

#ifdef WEBOS
	ComponentListRow themeDownloadRow;
	themeDownloadRow.addElement(std::make_shared<TextComponent>(mWindow,
		webosTr("DOWNLOAD THEMES", "THEMES HERUNTERLADEN"), Font::get(FONT_SIZE_MEDIUM), 0x777777FF), true);
	themeDownloadRow.addElement(makeArrow(mWindow), false);
	themeDownloadRow.makeAcceptInputHandler(std::bind(&GuiMenu::openWebOSThemeManager, this));
	s->addRow(themeDownloadRow);
#endif

	// theme set
	auto themeSets = ThemeData::getThemeSets();

	if(!themeSets.empty())
	{
		std::map<std::string, ThemeSet>::const_iterator selectedSet = themeSets.find(Settings::getInstance()->getString("ThemeSet"));
		if(selectedSet == themeSets.cend())
			selectedSet = themeSets.cbegin();

		auto theme_set = std::make_shared< OptionListComponent<std::string> >(mWindow, webosTr("THEME SET", "DESIGN"), false);
		for(auto it = themeSets.cbegin(); it != themeSets.cend(); it++)
			theme_set->add(it->first, it->first, it == selectedSet);
		s->addWithLabel(webosTr("THEME SET", "DESIGN"), theme_set);

		Window* window = mWindow;
		s->addSaveFunc([window, theme_set]
		{
			bool needReload = false;
			std::string oldTheme = Settings::getInstance()->getString("ThemeSet");
			if(oldTheme != theme_set->getSelected())
				needReload = true;

			Settings::getInstance()->setString("ThemeSet", theme_set->getSelected());

			if(needReload)
			{
				Scripting::fireEvent("theme-changed", theme_set->getSelected(), oldTheme);
				CollectionSystemManager::get()->updateSystemsList();
				ViewController::get()->reloadAll(true); // TODO - replace this with some sort of signal-based implementation
			}
		});
	}

	// GameList view style
	auto gamelist_style = std::make_shared< OptionListComponent<std::string> >(mWindow, "GAMELIST VIEW STYLE", false);
	std::vector<std::string> styles;
	styles.push_back("automatic");
	styles.push_back("basic");
	styles.push_back("detailed");
	styles.push_back("video");
	styles.push_back("grid");

	for (auto it = styles.cbegin(); it != styles.cend(); it++)
		gamelist_style->add(*it, *it, Settings::getInstance()->getString("GamelistViewStyle") == *it);
	s->addWithLabel("GAMELIST VIEW STYLE", gamelist_style);
	s->addSaveFunc([gamelist_style] {
		bool needReload = false;
		if (Settings::getInstance()->getString("GamelistViewStyle") != gamelist_style->getSelected())
			needReload = true;
		Settings::getInstance()->setString("GamelistViewStyle", gamelist_style->getSelected());
		if (needReload)
			ViewController::get()->reloadAll();
	});

	// Optionally ignore leading articles when sorting game titles
	auto ignore_articles = std::make_shared<SwitchComponent>(mWindow);
	ignore_articles->setState(Settings::getInstance()->getBool("IgnoreLeadingArticles"));
	s->addWithLabel("IGNORE ARTICLES (NAME SORT ONLY)", ignore_articles);
	s->addSaveFunc([ignore_articles, window] {
		bool articles_are_ignored = Settings::getInstance()->getBool("IgnoreLeadingArticles");
		Settings::getInstance()->setBool("IgnoreLeadingArticles", ignore_articles->getState());
		if (ignore_articles->getState() != articles_are_ignored)
		{
			//For each system...
			for (auto it = SystemData::sSystemVector.cbegin(); it != SystemData::sSystemVector.cend(); it++)
			{
				//Apply sort recursively
				FileData* root = (*it)->getRootFolder();
				root->sort(getSortTypeFromString(root->getSortName()));

				//Notify that the root folder was sorted
				ViewController::get()->getGameListView((*it))->onFileChanged(root, FILE_SORTED);
			}

			//Display popup to inform user
			GuiInfoPopup* popup = new GuiInfoPopup(window, "Files sorted", 4000);
			window->setInfoPopup(popup);
		}
	});

	// lb/rb uses full screen size paging instead of -10/+10 steps
	auto use_fullscreen_paging = std::make_shared<SwitchComponent>(mWindow);
	use_fullscreen_paging->setState(Settings::getInstance()->getBool("UseFullscreenPaging"));
	s->addWithLabel("USE FULL SCREEN PAGING FOR LB/RB", use_fullscreen_paging);
	s->addSaveFunc([use_fullscreen_paging] {
		Settings::getInstance()->setBool("UseFullscreenPaging", use_fullscreen_paging->getState());
	});

	// Optionally start in selected system
	auto systemfocus_list = std::make_shared< OptionListComponent<std::string> >(mWindow, "START ON SYSTEM", false);
	systemfocus_list->add("NONE", "", Settings::getInstance()->getString("StartupSystem") == "");
	for (auto it = SystemData::sSystemVector.cbegin(); it != SystemData::sSystemVector.cend(); it++)
	{
		if ("retropie" != (*it)->getName())
		{
			systemfocus_list->add((*it)->getName(), (*it)->getName(), Settings::getInstance()->getString("StartupSystem") == (*it)->getName());
		}
	}
	s->addWithLabel("START ON SYSTEM", systemfocus_list);
	s->addSaveFunc([systemfocus_list] {
		Settings::getInstance()->setString("StartupSystem", systemfocus_list->getSelected());
	});

	// show help
	auto show_help = std::make_shared<SwitchComponent>(mWindow);
	show_help->setState(Settings::getInstance()->getBool("ShowHelpPrompts"));
	s->addWithLabel(webosTr("ON-SCREEN HELP", "TASTENHINWEISE"), show_help);
	s->addSaveFunc([show_help] { Settings::getInstance()->setBool("ShowHelpPrompts", show_help->getState()); });

	// enable filters (ForceDisableFilters)
	auto enable_filter = std::make_shared<SwitchComponent>(mWindow);
	enable_filter->setState(!Settings::getInstance()->getBool("ForceDisableFilters"));
	s->addWithLabel("ENABLE FILTERS", enable_filter);
	s->addSaveFunc([enable_filter] {
		bool filter_is_enabled = !Settings::getInstance()->getBool("ForceDisableFilters");
		Settings::getInstance()->setBool("ForceDisableFilters", !enable_filter->getState());
		if (enable_filter->getState() != filter_is_enabled) ViewController::get()->ReloadAndGoToStart();
	});

	// hide start menu in Kid Mode
	auto disable_start = std::make_shared<SwitchComponent>(mWindow);
	disable_start->setState(Settings::getInstance()->getBool("DisableKidStartMenu"));
	s->addWithLabel("DISABLE START MENU IN KID MODE", disable_start);
	s->addSaveFunc([disable_start] { Settings::getInstance()->setBool("DisableKidStartMenu", disable_start->getState()); });

	mWindow->pushGui(s);

}

#ifdef WEBOS
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

void GuiMenu::openOtherSettings()
{
	auto s = new GuiSettings(mWindow, webosTr("OTHER SETTINGS", "WEITERE EINSTELLUNGEN"));

	// maximum vram
	auto max_vram = std::make_shared<SliderComponent>(mWindow, 0.f, 1000.f, 10.f, "Mb");
	max_vram->setValue((float)(Settings::getInstance()->getInt("MaxVRAM")));
	s->addWithLabel("VRAM LIMIT", max_vram);
	s->addSaveFunc([max_vram] { Settings::getInstance()->setInt("MaxVRAM", (int)Math::round(max_vram->getValue())); });

	// power saver
	auto power_saver = std::make_shared< OptionListComponent<std::string> >(mWindow, "POWER SAVER MODES", false);
	std::vector<std::string> modes;
	modes.push_back("disabled");
	modes.push_back("default");
	modes.push_back("enhanced");
	modes.push_back("instant");
	for (auto it = modes.cbegin(); it != modes.cend(); it++)
		power_saver->add(*it, *it, Settings::getInstance()->getString("PowerSaverMode") == *it);
	s->addWithLabel("POWER SAVER MODES", power_saver);
	s->addSaveFunc([this, power_saver] {
		if (Settings::getInstance()->getString("PowerSaverMode") != "instant" && power_saver->getSelected() == "instant") {
			Settings::getInstance()->setString("TransitionStyle", "instant");
			Settings::getInstance()->setBool("MoveCarousel", false);
			Settings::getInstance()->setBool("EnableSounds", false);
		}
		Settings::getInstance()->setString("PowerSaverMode", power_saver->getSelected());
		PowerSaver::init();
	});

	// gamelists
	auto gamelistsSaveMode = std::make_shared< OptionListComponent<std::string> >(mWindow, "SAVE METADATA", false);
	std::vector<std::string> saveModes;
	saveModes.push_back("on exit");
	saveModes.push_back("always");
	saveModes.push_back("never");

	for(auto it = saveModes.cbegin(); it != saveModes.cend(); it++)
		gamelistsSaveMode->add(*it, *it, Settings::getInstance()->getString("SaveGamelistsMode") == *it);
	s->addWithLabel("SAVE METADATA", gamelistsSaveMode);
	s->addSaveFunc([gamelistsSaveMode] {
		Settings::getInstance()->setString("SaveGamelistsMode", gamelistsSaveMode->getSelected());
	});

	auto parse_gamelists = std::make_shared<SwitchComponent>(mWindow);
	parse_gamelists->setState(Settings::getInstance()->getBool("ParseGamelistOnly"));
	s->addWithLabel("PARSE GAMESLISTS ONLY", parse_gamelists);
	s->addSaveFunc([parse_gamelists] { Settings::getInstance()->setBool("ParseGamelistOnly", parse_gamelists->getState()); });

	auto async_file_io = std::make_shared<SwitchComponent>(mWindow);
	async_file_io->setState(Settings::getInstance()->getBool("AsyncFileIO"));
	s->addWithLabel("ASYNC FILE IO", async_file_io);
	s->addSaveFunc([async_file_io] { Settings::getInstance()->setBool("AsyncFileIO", async_file_io->getState()); });

	auto local_art = std::make_shared<SwitchComponent>(mWindow);
	local_art->setState(Settings::getInstance()->getBool("LocalArt"));
	s->addWithLabel("SEARCH FOR LOCAL ART", local_art);
	s->addSaveFunc([local_art] { Settings::getInstance()->setBool("LocalArt", local_art->getState()); });

	// hidden files
	auto hidden_files = std::make_shared<SwitchComponent>(mWindow);
	hidden_files->setState(Settings::getInstance()->getBool("ShowHiddenFiles"));
	s->addWithLabel("SHOW HIDDEN FILES", hidden_files);
	s->addSaveFunc([hidden_files] { Settings::getInstance()->setBool("ShowHiddenFiles", hidden_files->getState()); });

#ifdef _OMX_
	// Video Player - VideoOmxPlayer
	auto omx_player = std::make_shared<SwitchComponent>(mWindow);
	omx_player->setState(Settings::getInstance()->getBool("VideoOmxPlayer"));
	s->addWithLabel("USE OMX PLAYER (HW ACCELERATED)", omx_player);
	s->addSaveFunc([omx_player]
	{
		// need to reload all views to re-create the right video components
		bool needReload = false;
		if(Settings::getInstance()->getBool("VideoOmxPlayer") != omx_player->getState())
			needReload = true;

		Settings::getInstance()->setBool("VideoOmxPlayer", omx_player->getState());

		if(needReload)
			ViewController::get()->reloadAll();
	});

#endif

	// hidden files
	auto background_indexing = std::make_shared<SwitchComponent>(mWindow);
	background_indexing->setState(Settings::getInstance()->getBool("BackgroundIndexing"));
	s->addWithLabel("INDEX FILES DURING SCREENSAVER", background_indexing);
	s->addSaveFunc([background_indexing] { Settings::getInstance()->setBool("BackgroundIndexing", background_indexing->getState()); });

	// framerate
	auto framerate = std::make_shared<SwitchComponent>(mWindow);
	framerate->setState(Settings::getInstance()->getBool("DrawFramerate"));
	s->addWithLabel("SHOW FRAMERATE", framerate);
	s->addSaveFunc([framerate] { Settings::getInstance()->setBool("DrawFramerate", framerate->getState()); });


	mWindow->pushGui(s);

}

void GuiMenu::openConfigInput()
{
	Window* window = mWindow;
	window->pushGui(new GuiMsgBox(window, "ARE YOU SURE YOU WANT TO CONFIGURE INPUT?", "YES",
		[window] {
		window->pushGui(new GuiDetectDevice(window, false, nullptr));
	}, "NO", nullptr)
	);

}

void GuiMenu::openQuitMenu()
{
	auto s = new GuiSettings(mWindow, webosTr("QUIT", "BEENDEN"));

	Window* window = mWindow;

	// command line switch
#ifdef WEBOS
	// A TV remote can trigger quit very easily, so always confirm it.
	bool confirm_quit = true;
#else
	bool confirm_quit = Settings::getInstance()->getBool("ConfirmQuit");
#endif

	ComponentListRow row;
	if (UIModeController::getInstance()->isUIModeFull())
	{
		auto static restart_es_fx = []() {
			Scripting::fireEvent("quit");
			if (quitES(QuitMode::RESTART)) {
				LOG(LogWarning) << "Restart terminated with non-zero result!";
			}
		};

		if (confirm_quit) {
			row.makeAcceptInputHandler([window] {
				window->pushGui(new GuiMsgBox(window, "REALLY RESTART?", "YES", restart_es_fx, "NO", nullptr));
			});
		} else {
			row.makeAcceptInputHandler(restart_es_fx);
		}
		row.addElement(std::make_shared<TextComponent>(window, "RESTART EMULATIONSTATION", Font::get(FONT_SIZE_MEDIUM), 0x777777FF), true);
		s->addRow(row);

#ifdef WEBOS
		if(true)
#else
		if(Settings::getInstance()->getBool("ShowExit"))
#endif
		{
			auto static quit_es_fx = [] {
				Scripting::fireEvent("quit");
				quitES();
			};

			row.elements.clear();
			if (confirm_quit) {
				row.makeAcceptInputHandler([window] {
					window->pushGui(new GuiMsgBox(window, "REALLY QUIT?", "YES", quit_es_fx, "NO", nullptr));
				});
			} else {
				row.makeAcceptInputHandler(quit_es_fx);
			}
			row.addElement(std::make_shared<TextComponent>(window, "QUIT EMULATIONSTATION", Font::get(FONT_SIZE_MEDIUM), 0x777777FF), true);
			s->addRow(row);
		}
	}

#ifndef WEBOS
	auto static reboot_sys_fx = [] {
		Scripting::fireEvent("quit", "reboot");
		Scripting::fireEvent("reboot");
		if (quitES(QuitMode::REBOOT)) {
			LOG(LogWarning) << "Restart terminated with non-zero result!";
		}
	};

	row.elements.clear();
	if (confirm_quit) {
		row.makeAcceptInputHandler([window] {
			window->pushGui(new GuiMsgBox(window, "REALLY RESTART?", "YES", {reboot_sys_fx}, "NO", nullptr));
		});
	} else {
		row.makeAcceptInputHandler(reboot_sys_fx);
	}
	row.addElement(std::make_shared<TextComponent>(window, "RESTART SYSTEM", Font::get(FONT_SIZE_MEDIUM), 0x777777FF), true);
	s->addRow(row);

	auto static shutdown_sys_fx = [] {
		Scripting::fireEvent("quit", "shutdown");
		Scripting::fireEvent("shutdown");
		if (quitES(QuitMode::SHUTDOWN)) {
			LOG(LogWarning) << "Shutdown terminated with non-zero result!";
		}
	};

	row.elements.clear();
	if (confirm_quit) {
		row.makeAcceptInputHandler([window] {
			window->pushGui(new GuiMsgBox(window, "REALLY SHUTDOWN?", "YES", shutdown_sys_fx, "NO", nullptr));
		});
	} else {
		row.makeAcceptInputHandler(shutdown_sys_fx);
	}
	row.addElement(std::make_shared<TextComponent>(window, "SHUTDOWN SYSTEM", Font::get(FONT_SIZE_MEDIUM), 0x777777FF), true);
	s->addRow(row);
#endif

	mWindow->pushGui(s);
}

void GuiMenu::addVersionInfo()
{
	std::string  buildDate = (Settings::getInstance()->getBool("Debug") ? std::string( "   (" + Utils::String::toUpper(PROGRAM_BUILT_STRING) + ")") : (""));

	mVersion.setFont(Font::get(FONT_SIZE_SMALL));
	mVersion.setColor(0x5E5E5EFF);
	mVersion.setText("EMULATIONSTATION V" + Utils::String::toUpper(PROGRAM_VERSION_STRING) + buildDate);
	mVersion.setHorizontalAlignment(ALIGN_CENTER);
	addChild(&mVersion);
}

void GuiMenu::openScreensaverOptions() {
	mWindow->pushGui(new GuiGeneralScreensaverOptions(mWindow, webosTr("SCREENSAVER SETTINGS", "BILDSCHIRMSCHONER")));
}

void GuiMenu::openCollectionSystemSettings() {
	mWindow->pushGui(new GuiCollectionSystemsOptions(mWindow));
}

void GuiMenu::onSizeChanged()
{
	mVersion.setSize(mSize.x(), 0);
	mVersion.setPosition(0, mSize.y() - mVersion.getSize().y());
}

void GuiMenu::addEntry(const char* name, unsigned int color, bool add_arrow, const std::function<void()>& func)
{
	std::shared_ptr<Font> font = Font::get(FONT_SIZE_MEDIUM);

	// populate the list
	ComponentListRow row;
	row.addElement(std::make_shared<TextComponent>(mWindow, name, font, color), true);

	if(add_arrow)
	{
		std::shared_ptr<ImageComponent> bracket = makeArrow(mWindow);
		row.addElement(bracket, false);
	}

	row.makeAcceptInputHandler(func);

	mMenu.addRow(row);
}

bool GuiMenu::input(InputConfig* config, Input input)
{
	if(GuiComponent::input(config, input))
		return true;

	if((config->isMappedTo("b", input) || config->isMappedTo("start", input)) && input.value != 0)
	{
		delete this;
		return true;
	}

	return false;
}

HelpStyle GuiMenu::getHelpStyle()
{
	HelpStyle style = HelpStyle();
	style.applyTheme(ViewController::get()->getState().getSystem()->getTheme(), "system");
	return style;
}

std::vector<HelpPrompt> GuiMenu::getHelpPrompts()
{
	std::vector<HelpPrompt> prompts;
	prompts.push_back(HelpPrompt("up/down", "choose"));
	prompts.push_back(HelpPrompt("a", "select"));
	prompts.push_back(HelpPrompt("start", "close"));
	return prompts;
}
