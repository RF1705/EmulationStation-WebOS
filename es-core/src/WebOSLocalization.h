#pragma once
#ifndef ES_CORE_WEBOS_LOCALIZATION_H
#define ES_CORE_WEBOS_LOCALIZATION_H

#include "Settings.h"
#include <rapidjson/document.h>
#include <rapidjson/filereadstream.h>
#include <cstdio>
#include <map>
#include <string>
#include <vector>

struct WebOSLanguageInfo
{
    const char* code;
    const char* nativeName;
};

inline const std::vector<WebOSLanguageInfo>& webosLanguages()
{
    static const std::vector<WebOSLanguageInfo> languages = {
        {"de", "Deutsch"}, {"en", "English"}, {"fr", "Français"}, {"es", "Español"},
        {"it", "Italiano"}, {"nl", "Nederlands"}, {"pt", "Português"}, {"pl", "Polski"}
    };
    return languages;
}

inline std::string webosCurrentLanguage()
{
#ifdef WEBOS
    std::string language = Settings::getInstance()->getString("WebOSLanguage");
    if(language.empty())
        language = "de";
    for(const auto& candidate : webosLanguages())
        if(language == candidate.code)
            return language;
    return "en";
#else
    return "en";
#endif
}

inline std::map<std::string, std::string> webosLoadTranslationFile(const std::string& language)
{
    std::map<std::string, std::string> values;
    const std::string path = "resources/i18n/" + language + ".json";
    FILE* file = fopen(path.c_str(), "rb");
    if(!file)
        return values;

    char buffer[65536];
    rapidjson::FileReadStream stream(file, buffer, sizeof(buffer));
    rapidjson::Document document;
    document.ParseStream(stream);
    fclose(file);

    if(!document.IsObject())
        return values;

    for(auto it = document.MemberBegin(); it != document.MemberEnd(); ++it)
        if(it->name.IsString() && it->value.IsString())
            values[it->name.GetString()] = it->value.GetString();
    return values;
}

inline const std::map<std::string, std::string>& webosTranslationTable(const std::string& language)
{
    static std::map<std::string, std::map<std::string, std::string>> cache;
    auto found = cache.find(language);
    if(found == cache.end())
        found = cache.insert(std::make_pair(language, webosLoadTranslationFile(language))).first;
    return found->second;
}

inline const char* webosTr(const char* key, const char* englishFallback)
{
#ifdef WEBOS
    const std::string language = webosCurrentLanguage();
    const auto& selected = webosTranslationTable(language);
    auto found = selected.find(key);
    if(found != selected.end())
        return found->second.c_str();

    if(language != "en")
    {
        const auto& english = webosTranslationTable("en");
        found = english.find(key);
        if(found != english.end())
            return found->second.c_str();
    }
#endif
    return englishFallback;
}

inline std::string webosTrString(const char* key, const char* englishFallback)
{
    return std::string(webosTr(key, englishFallback));
}

// Compatibility for webOS text that has not been moved to a stable key yet.
// Non-German languages deliberately fall back to English.
inline const char* webosTrLegacy(const char* english, const char* german)
{
#ifdef WEBOS
    return webosCurrentLanguage() == "de" ? german : english;
#else
    return english;
#endif
}

inline std::string webosTrStringLegacy(const char* english, const char* german)
{
    return std::string(webosTrLegacy(english, german));
}

#endif
