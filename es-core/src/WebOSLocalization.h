#pragma once
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
