#include "WebOSThemeManager.h"

#ifdef WEBOS
#include "Log.h"
#include "Settings.h"
#include "ThemeData.h"
#include "WebOSLocalization.h"
#include "utils/FileSystemUtil.h"
#include <curl/curl.h>
#include <zip.h>
#include <cstdio>
#include <unistd.h>

static const std::vector<WebOSThemeEntry> sThemes = {
    {"Carbon", "carbon", "https://codeload.github.com/RetroPie/es-theme-carbon/zip/b09973e0b0c589cb11fe772c169a6ff5d588b390"},
    {"Simple", "simple", "https://codeload.github.com/RetroPie/es-theme-simple/zip/5a6c1daf965b9d410398243c232a34911dad8826"},
    {"Simple Dark", "simple-dark", "https://codeload.github.com/RetroPie/es-theme-simple-dark/zip/058472cfbc3b4fe9ddf1ab452908fab40e32d29c"},
};
static const char* sBundledSimpleDarkArchive = "resources/bundled-themes/simple-dark.zip";

const std::vector<WebOSThemeEntry>& webosThemes()
{
    return sThemes;
}

static std::string themeRoot()
{
    return Utils::FileSystem::getHomePath() + "/.emulationstation/themes";
}

static std::string themePath(const WebOSThemeEntry& theme)
{
    return themeRoot() + "/" + theme.folderName;
}

bool webosThemeInstalled(const WebOSThemeEntry& theme)
{
    return Utils::FileSystem::isDirectory(themePath(theme));
}

static bool removeDirectory(const std::string& path)
{
    if(!Utils::FileSystem::exists(path))
        return true;
    if(Utils::FileSystem::isSymlink(path) || Utils::FileSystem::isRegularFile(path))
        return Utils::FileSystem::removeFile(path);
    if(!Utils::FileSystem::isDirectory(path))
        return false;

    for(const std::string& entry : Utils::FileSystem::getDirContent(path, false))
    {
        if(Utils::FileSystem::isSymlink(entry) || Utils::FileSystem::isRegularFile(entry))
        {
            if(!Utils::FileSystem::removeFile(entry))
                return false;
        }
        else if(Utils::FileSystem::isDirectory(entry) && !removeDirectory(entry))
            return false;
    }
    return rmdir(path.c_str()) == 0;
}

static void tryRemoveBundledSimpleDarkArchive()
{
    if(!Utils::FileSystem::isRegularFile(sBundledSimpleDarkArchive))
        return;

    if(Utils::FileSystem::removeFile(sBundledSimpleDarkArchive))
        LOG(LogInfo) << "webOS theme manager: removed bundled Simple Dark archive after seeding";
}

static bool downloadFile(const std::string& url, const std::string& path, std::string& error)
{
    FILE* output = fopen(path.c_str(), "wb");
    if(!output)
    {
        error = webosTr("theme.error.temp_file", "Could not create temporary download file.");
        return false;
    }

    CURL* curl = curl_easy_init();
    if(!curl)
    {
        fclose(output);
        error = webosTr("theme.error.downloader", "Could not initialize downloader.");
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
        error = std::string(webosTr("theme.error.download_prefix", "Download failed: ")) + curl_easy_strerror(result);
        return false;
    }
    return true;
}

static bool safeArchivePath(const std::string& path)
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

static bool extractTheme(const std::string& archivePath, const WebOSThemeEntry& theme, std::string& error)
{
    int zipError = 0;
    zip_t* archive = zip_open(archivePath.c_str(), ZIP_RDONLY, &zipError);
    if(!archive)
    {
        error = webosTr("theme.error.archive_open", "Theme archive could not be opened.");
        return false;
    }

    const std::string destinationRoot = themePath(theme);
    if(Utils::FileSystem::exists(destinationRoot) && !removeDirectory(destinationRoot))
    {
        zip_close(archive);
        error = webosTr("theme.error.remove", "Could not remove the theme directory.");
        return false;
    }
    if(!Utils::FileSystem::createDirectory(destinationRoot))
    {
        zip_close(archive);
        error = webosTr("theme.error.directory", "Theme directory could not be created.");
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
        if(!safeArchivePath(relative))
        {
            zip_close(archive);
            error = webosTr("theme.error.unsafe_path", "Unsafe path in theme archive.");
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
            error = webosTr("theme.error.invalid_file", "Theme archive contains an invalid or oversized file.");
            return false;
        }
        totalSize += stat.size;
        if(totalSize > maxTotalSize)
        {
            zip_close(archive);
            error = webosTr("theme.error.too_large", "Theme archive is too large.");
            return false;
        }

        const std::string parent = Utils::FileSystem::getParent(destination);
        if(!Utils::FileSystem::createDirectory(parent))
        {
            zip_close(archive);
            error = std::string(webosTr("theme.error.directory_prefix", "Could not create theme directory: ")) + parent;
            return false;
        }

        zip_file_t* input = zip_fopen_index(archive, i, 0);
        if(!input)
        {
            zip_close(archive);
            error = webosTr("theme.error.read_file", "Could not read a file from the theme archive.");
            return false;
        }
        FILE* output = fopen(destination.c_str(), "wb");
        if(!output)
        {
            zip_fclose(input);
            zip_close(archive);
            error = webosTr("theme.error.write_file", "Could not write a theme file.");
            return false;
        }

        char buffer[32768];
        zip_int64_t bytes = 0;
        bool ok = true;
        while((bytes = zip_fread(input, buffer, sizeof(buffer))) > 0)
            if(fwrite(buffer, 1, (size_t)bytes, output) != (size_t)bytes)
            {
                ok = false;
                break;
            }
        if(bytes < 0)
            ok = false;
        fclose(output);
        zip_fclose(input);
        if(!ok)
        {
            zip_close(archive);
            error = webosTr("theme.error.extract", "Could not extract the complete theme.");
            return false;
        }
    }

    zip_close(archive);
    return true;
}

bool webosInstallTheme(const WebOSThemeEntry& theme, std::string& error)
{
    const std::string configRoot = Utils::FileSystem::getHomePath() + "/.emulationstation";
    if(!Utils::FileSystem::createDirectory(themeRoot()))
    {
        error = std::string(webosTr("theme.error.directory_prefix", "Could not create theme directory: ")) + themeRoot();
        return false;
    }

    if(std::string(theme.folderName) == "simple-dark" && Utils::FileSystem::isRegularFile(sBundledSimpleDarkArchive))
        return extractTheme(sBundledSimpleDarkArchive, theme, error);

    const std::string archivePath = configRoot + "/theme-download.zip";
    if(!downloadFile(theme.archiveUrl, archivePath, error))
        return false;
    const bool extracted = extractTheme(archivePath, theme, error);
    Utils::FileSystem::removeFile(archivePath);
    return extracted;
}

bool webosDeleteTheme(const WebOSThemeEntry& theme, std::string& error, bool& activeThemeChanged, std::string& replacementTheme)
{
    activeThemeChanged = Settings::getInstance()->getString("ThemeSet") == theme.folderName;
    replacementTheme.clear();
    if(!removeDirectory(themePath(theme)))
    {
        error = webosTr("theme.error.remove", "Could not remove the theme directory.");
        return false;
    }

    if(activeThemeChanged)
    {
        const auto remaining = ThemeData::getThemeSets();
        if(!remaining.empty())
            replacementTheme = remaining.begin()->first;
        Settings::getInstance()->setString("ThemeSet", replacementTheme);
        Settings::getInstance()->saveFile();
    }
    return true;
}

bool webosEnsureBundledDefaultTheme(std::string& error)
{
    Settings* settings = Settings::getInstance();
    if(settings->getBool("WebOSBundledSimpleDarkSeeded"))
    {
        // App updates may restore packaged resources. Once Simple Dark has
        // already been seeded, release the one-shot archive again if webOS
        // exposes the installed app directory as writable.
        tryRemoveBundledSimpleDarkArchive();
        return true;
    }

    const WebOSThemeEntry* simpleDark = nullptr;
    for(const auto& theme : sThemes)
        if(std::string(theme.folderName) == "simple-dark")
            simpleDark = &theme;
    if(!simpleDark)
        return false;

    if(!webosThemeInstalled(*simpleDark))
    {
        if(!Utils::FileSystem::isRegularFile(sBundledSimpleDarkArchive))
        {
            error = webosTr("theme.error.bundled_missing", "The bundled Simple Dark theme archive is missing.");
            return false;
        }
        if(!webosInstallTheme(*simpleDark, error))
            return false;
    }

    if(settings->getString("ThemeSet").empty())
        settings->setString("ThemeSet", "simple-dark");
    settings->setBool("WebOSBundledSimpleDarkSeeded", true);
    settings->saveFile();
    tryRemoveBundledSimpleDarkArchive();
    return true;
}
#endif