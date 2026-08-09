#pragma once
#ifndef ES_APP_WEBOS_THEME_MANAGER_H
#define ES_APP_WEBOS_THEME_MANAGER_H

#ifdef WEBOS
#include <string>
#include <vector>

struct WebOSThemeEntry
{
    const char* displayName;
    const char* folderName;
    const char* archiveUrl;
};

const std::vector<WebOSThemeEntry>& webosThemes();
bool webosThemeInstalled(const WebOSThemeEntry& theme);
bool webosInstallTheme(const WebOSThemeEntry& theme, std::string& error);
bool webosDeleteTheme(const WebOSThemeEntry& theme, std::string& error, bool& activeThemeChanged, std::string& replacementTheme);
bool webosEnsureBundledDefaultTheme(std::string& error);
#endif

#endif
