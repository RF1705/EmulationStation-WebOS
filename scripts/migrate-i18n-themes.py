#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# First put every existing two-string translation call behind an explicit
# compatibility name. New code below uses stable translation keys.
for base in (ROOT / "es-app", ROOT / "es-core"):
    for path in list(base.rglob("*.cpp")) + list(base.rglob("*.h")):
        text = path.read_text()
        text = text.replace("webosTrString(", "webosTrStringLegacy(")
        text = text.replace("webosTr(", "webosTrLegacy(")
        path.write_text(text)

languages = {
    "en": {
        "common.open": "open",
        "common.back": "back",
        "common.yes": "YES",
        "common.no": "NO",
        "common.ok": "OK",
        "common.delete": "DELETE",
        "common.cancel": "CANCEL",
        "common.installed_suffix": " (installed)",
        "menu.main": "MAIN MENU",
        "menu.games_systems": "GAMES & SYSTEMS",
        "menu.scraper": "SCRAPER",
        "menu.sound_settings": "SOUND SETTINGS",
        "menu.ui_settings": "UI SETTINGS",
        "menu.collections": "GAME COLLECTION SETTINGS",
        "menu.other_settings": "OTHER SETTINGS",
        "menu.configure_input": "CONFIGURE INPUT",
        "menu.quit": "QUIT",
        "games.select_folder": "SELECT GAME FOLDER",
        "games.select_this_folder": "SELECT THIS FOLDER",
        "games.use_this_directory": "use this directory",
        "games.info": "Enable a system and set its game folder. Changes are saved when you go back; restart EmulationStation to rescan games.",
        "games.game_folder": "GAME FOLDER",
        "games.save_error": "Could not save the systems configuration.",
        "scraper.source": "SCRAPE FROM",
        "scraper.language": "SCRAPER LANGUAGE",
        "scraper.language_label": "LANGUAGE (SCREENSCRAPER)",
        "scraper.region": "SCRAPER REGION",
        "scraper.region_label": "REGION (SCREENSCRAPER)",
        "scraper.ratings": "SCRAPE RATINGS",
        "scraper.now": "SCRAPE NOW",
        "region.europe": "Europe",
        "region.japan": "Japan",
        "region.world": "World",
        "sound.system_volume": "SYSTEM VOLUME",
        "sound.navigation_sounds": "ENABLE NAVIGATION SOUNDS",
        "sound.video_audio": "ENABLE VIDEO AUDIO",
        "ui.language": "LANGUAGE",
        "ui.mode": "UI MODE",
        "ui.screensaver": "SCREENSAVER SETTINGS",
        "ui.quick_system_select": "QUICK SYSTEM SELECT",
        "ui.transition_style": "TRANSITION STYLE",
        "ui.theme_manager": "THEME MANAGER",
        "ui.theme_set": "THEME SET",
        "ui.on_screen_help": "ON-SCREEN HELP",
        "theme.info": "Install or remove themes. Simple Dark is included with the app; other themes are downloaded from the official RetroPie repositories.",
        "theme.install_failed": "Theme installation failed.\n\n",
        "theme.installed_apply": " was installed.\nApply this theme now?",
        "theme.delete_question": "Delete this theme?",
        "theme.deleted": "Theme deleted.",
        "theme.delete_failed": "Theme could not be deleted.\n\n",
        "theme.error.temp_file": "Could not create temporary download file.",
        "theme.error.downloader": "Could not initialize downloader.",
        "theme.error.download_prefix": "Download failed: ",
        "theme.error.archive_open": "Theme archive could not be opened.",
        "theme.error.directory": "Theme directory could not be created.",
        "theme.error.unsafe_path": "Unsafe path in theme archive.",
        "theme.error.invalid_file": "Theme archive contains an invalid or oversized file.",
        "theme.error.too_large": "Theme archive is too large.",
        "theme.error.directory_prefix": "Could not create theme directory: ",
        "theme.error.read_file": "Could not read a file from the theme archive.",
        "theme.error.write_file": "Could not write a theme file.",
        "theme.error.extract": "Could not extract the complete theme.",
        "theme.error.remove": "Could not remove the theme directory.",
        "theme.error.bundled_missing": "The bundled Simple Dark theme archive is missing.",
        "quit.really_quit_es": "REALLY QUIT EMULATIONSTATION?",
        "quit.really_restart": "REALLY RESTART?",
        "quit.restart_es": "RESTART EMULATIONSTATION",
        "quit.really_quit": "REALLY QUIT?",
        "quit.quit_es": "QUIT EMULATIONSTATION"
    },
    "de": {
        "common.open": "öffnen", "common.back": "zurück", "common.yes": "JA", "common.no": "NEIN", "common.ok": "OK", "common.delete": "LÖSCHEN", "common.cancel": "ABBRECHEN", "common.installed_suffix": " (installiert)",
        "menu.main": "HAUPTMENÜ", "menu.games_systems": "SPIELE & SYSTEME", "menu.scraper": "SPIELINFORMATIONEN", "menu.sound_settings": "TONEINSTELLUNGEN", "menu.ui_settings": "OBERFLÄCHE", "menu.collections": "SPIELESAMMLUNGEN", "menu.other_settings": "WEITERE EINSTELLUNGEN", "menu.configure_input": "STEUERUNG EINRICHTEN", "menu.quit": "BEENDEN",
        "games.select_folder": "SPIELEORDNER WÄHLEN", "games.select_this_folder": "DIESEN ORDNER WÄHLEN", "games.use_this_directory": "diesen Ordner verwenden", "games.info": "System aktivieren und Spieleordner setzen. Beim Zurückgehen wird gespeichert; danach EmulationStation neu starten.", "games.game_folder": "SPIELEORDNER", "games.save_error": "Systemkonfiguration konnte nicht gespeichert werden.",
        "scraper.source": "DATENQUELLE", "scraper.language": "SCRAPER-SPRACHE", "scraper.language_label": "SPRACHE (SCREENSCRAPER)", "scraper.region": "SCRAPER-REGION", "scraper.region_label": "REGION (SCREENSCRAPER)", "scraper.ratings": "BEWERTUNGEN LADEN", "scraper.now": "JETZT LADEN",
        "region.europe": "Europa", "region.japan": "Japan", "region.world": "Welt",
        "sound.system_volume": "SYSTEMLAUTSTÄRKE", "sound.navigation_sounds": "NAVIGATIONSTÖNE", "sound.video_audio": "VIDEO-TON",
        "ui.language": "SPRACHE", "ui.mode": "UI-MODUS", "ui.screensaver": "BILDSCHIRMSCHONER", "ui.quick_system_select": "SCHNELLER SYSTEMWECHSEL", "ui.transition_style": "ÜBERGANG", "ui.theme_manager": "THEME-VERWALTUNG", "ui.theme_set": "DESIGN", "ui.on_screen_help": "TASTENHINWEISE",
        "theme.info": "Themes installieren oder löschen. Simple Dark ist in der App enthalten; weitere Themes werden aus den offiziellen RetroPie-Repositories geladen.", "theme.install_failed": "Theme-Installation fehlgeschlagen.\n\n", "theme.installed_apply": " wurde installiert.\nDieses Theme jetzt anwenden?", "theme.delete_question": "Dieses Theme wirklich löschen?", "theme.deleted": "Theme gelöscht.", "theme.delete_failed": "Theme konnte nicht gelöscht werden.\n\n",
        "theme.error.temp_file": "Temporäre Download-Datei konnte nicht erstellt werden.", "theme.error.downloader": "Downloader konnte nicht initialisiert werden.", "theme.error.download_prefix": "Download fehlgeschlagen: ", "theme.error.archive_open": "Theme-Archiv konnte nicht geöffnet werden.", "theme.error.directory": "Theme-Verzeichnis konnte nicht erstellt werden.", "theme.error.unsafe_path": "Unsicherer Pfad im Theme-Archiv.", "theme.error.invalid_file": "Theme-Archiv enthält eine ungültige oder zu große Datei.", "theme.error.too_large": "Theme-Archiv ist zu groß.", "theme.error.directory_prefix": "Theme-Verzeichnis konnte nicht erstellt werden: ", "theme.error.read_file": "Datei im Theme-Archiv konnte nicht gelesen werden.", "theme.error.write_file": "Theme-Datei konnte nicht geschrieben werden.", "theme.error.extract": "Theme konnte nicht vollständig entpackt werden.", "theme.error.remove": "Theme-Verzeichnis konnte nicht gelöscht werden.", "theme.error.bundled_missing": "Das mitgelieferte Simple-Dark-Theme-Archiv fehlt.",
        "quit.really_quit_es": "EMULATIONSTATION WIRKLICH BEENDEN?", "quit.really_restart": "WIRKLICH NEU STARTEN?", "quit.restart_es": "EMULATIONSTATION NEU STARTEN", "quit.really_quit": "WIRKLICH BEENDEN?", "quit.quit_es": "EMULATIONSTATION BEENDEN"
    },
    "fr": {
        "common.open": "ouvrir", "common.back": "retour", "common.yes": "OUI", "common.no": "NON", "common.ok": "OK", "common.delete": "SUPPRIMER", "common.cancel": "ANNULER", "common.installed_suffix": " (installé)",
        "menu.main": "MENU PRINCIPAL", "menu.games_systems": "JEUX & SYSTÈMES", "menu.scraper": "INFORMATIONS DES JEUX", "menu.sound_settings": "PARAMÈTRES AUDIO", "menu.ui_settings": "INTERFACE", "menu.collections": "COLLECTIONS DE JEUX", "menu.other_settings": "AUTRES PARAMÈTRES", "menu.configure_input": "CONFIGURER LES COMMANDES", "menu.quit": "QUITTER",
        "games.select_folder": "CHOISIR LE DOSSIER DES JEUX", "games.select_this_folder": "CHOISIR CE DOSSIER", "games.use_this_directory": "utiliser ce dossier", "games.game_folder": "DOSSIER DES JEUX", "games.save_error": "Impossible d’enregistrer la configuration des systèmes.",
        "scraper.source": "SOURCE", "scraper.language": "LANGUE DU SCRAPER", "scraper.language_label": "LANGUE (SCREENSCRAPER)", "scraper.region": "RÉGION DU SCRAPER", "scraper.region_label": "RÉGION (SCREENSCRAPER)", "scraper.ratings": "TÉLÉCHARGER LES NOTES", "scraper.now": "LANCER MAINTENANT",
        "region.europe": "Europe", "region.japan": "Japon", "region.world": "Monde",
        "sound.system_volume": "VOLUME SYSTÈME", "sound.navigation_sounds": "SONS DE NAVIGATION", "sound.video_audio": "SON DES VIDÉOS",
        "ui.language": "LANGUE", "ui.mode": "MODE D’INTERFACE", "ui.screensaver": "ÉCONOMISEUR D’ÉCRAN", "ui.quick_system_select": "SÉLECTION RAPIDE DU SYSTÈME", "ui.transition_style": "STYLE DE TRANSITION", "ui.theme_manager": "GESTION DES THÈMES", "ui.theme_set": "THÈME", "ui.on_screen_help": "AIDE À L’ÉCRAN",
        "theme.info": "Installez ou supprimez des thèmes. Simple Dark est inclus dans l’application ; les autres thèmes proviennent des dépôts RetroPie officiels.", "theme.install_failed": "Échec de l’installation du thème.\n\n", "theme.installed_apply": " a été installé.\nAppliquer ce thème maintenant ?", "theme.delete_question": "Supprimer ce thème ?", "theme.deleted": "Thème supprimé.", "theme.delete_failed": "Impossible de supprimer le thème.\n\n",
        "quit.really_quit_es": "VRAIMENT QUITTER EMULATIONSTATION?", "quit.really_restart": "VRAIMENT REDÉMARRER ?", "quit.restart_es": "REDÉMARRER EMULATIONSTATION", "quit.really_quit": "VRAIMENT QUITTER ?", "quit.quit_es": "QUITTER EMULATIONSTATION"
    },
    "es": {
        "common.open": "abrir", "common.back": "atrás", "common.yes": "SÍ", "common.no": "NO", "common.ok": "OK", "common.delete": "ELIMINAR", "common.cancel": "CANCELAR", "common.installed_suffix": " (instalado)",
        "menu.main": "MENÚ PRINCIPAL", "menu.games_systems": "JUEGOS Y SISTEMAS", "menu.scraper": "INFORMACIÓN DE JUEGOS", "menu.sound_settings": "AJUSTES DE SONIDO", "menu.ui_settings": "INTERFAZ", "menu.collections": "COLECCIONES DE JUEGOS", "menu.other_settings": "OTROS AJUSTES", "menu.configure_input": "CONFIGURAR CONTROLES", "menu.quit": "SALIR",
        "games.select_folder": "ELEGIR CARPETA DE JUEGOS", "games.select_this_folder": "ELEGIR ESTA CARPETA", "games.use_this_directory": "usar esta carpeta", "games.game_folder": "CARPETA DE JUEGOS", "games.save_error": "No se pudo guardar la configuración de sistemas.",
        "scraper.source": "FUENTE", "scraper.language": "IDIOMA DEL SCRAPER", "scraper.language_label": "IDIOMA (SCREENSCRAPER)", "scraper.region": "REGIÓN DEL SCRAPER", "scraper.region_label": "REGIÓN (SCREENSCRAPER)", "scraper.ratings": "DESCARGAR VALORACIONES", "scraper.now": "DESCARGAR AHORA",
        "region.europe": "Europa", "region.japan": "Japón", "region.world": "Mundo",
        "sound.system_volume": "VOLUMEN DEL SISTEMA", "sound.navigation_sounds": "SONIDOS DE NAVEGACIÓN", "sound.video_audio": "AUDIO DE VÍDEO",
        "ui.language": "IDIOMA", "ui.mode": "MODO DE INTERFAZ", "ui.screensaver": "SALVAPANTALLAS", "ui.quick_system_select": "CAMBIO RÁPIDO DE SISTEMA", "ui.transition_style": "ESTILO DE TRANSICIÓN", "ui.theme_manager": "GESTOR DE TEMAS", "ui.theme_set": "TEMA", "ui.on_screen_help": "AYUDA EN PANTALLA",
        "theme.info": "Instala o elimina temas. Simple Dark está incluido con la aplicación; los demás temas se descargan de los repositorios oficiales de RetroPie.", "theme.install_failed": "Error al instalar el tema.\n\n", "theme.installed_apply": " se ha instalado.\n¿Aplicar este tema ahora?", "theme.delete_question": "¿Eliminar este tema?", "theme.deleted": "Tema eliminado.", "theme.delete_failed": "No se pudo eliminar el tema.\n\n",
        "quit.really_quit_es": "¿SALIR REALMENTE DE EMULATIONSTATION?", "quit.really_restart": "¿REINICIAR REALMENTE?", "quit.restart_es": "REINICIAR EMULATIONSTATION", "quit.really_quit": "¿SALIR REALMENTE?", "quit.quit_es": "SALIR DE EMULATIONSTATION"
    },
    "it": {
        "common.open": "apri", "common.back": "indietro", "common.yes": "SÌ", "common.no": "NO", "common.ok": "OK", "common.delete": "ELIMINA", "common.cancel": "ANNULLA", "common.installed_suffix": " (installato)",
        "menu.main": "MENU PRINCIPALE", "menu.games_systems": "GIOCHI E SISTEMI", "menu.scraper": "INFORMAZIONI GIOCHI", "menu.sound_settings": "IMPOSTAZIONI AUDIO", "menu.ui_settings": "INTERFACCIA", "menu.collections": "COLLEZIONI DI GIOCHI", "menu.other_settings": "ALTRE IMPOSTAZIONI", "menu.configure_input": "CONFIGURA CONTROLLI", "menu.quit": "ESCI",
        "games.select_folder": "SCEGLI CARTELLA GIOCHI", "games.select_this_folder": "SCEGLI QUESTA CARTELLA", "games.use_this_directory": "usa questa cartella", "games.game_folder": "CARTELLA GIOCHI", "games.save_error": "Impossibile salvare la configurazione dei sistemi.",
        "scraper.source": "FONTE", "scraper.language": "LINGUA SCRAPER", "scraper.language_label": "LINGUA (SCREENSCRAPER)", "scraper.region": "REGIONE SCRAPER", "scraper.region_label": "REGIONE (SCREENSCRAPER)", "scraper.ratings": "SCARICA VALUTAZIONI", "scraper.now": "SCARICA ORA",
        "region.europe": "Europa", "region.japan": "Giappone", "region.world": "Mondo",
        "sound.system_volume": "VOLUME SISTEMA", "sound.navigation_sounds": "SUONI DI NAVIGAZIONE", "sound.video_audio": "AUDIO VIDEO",
        "ui.language": "LINGUA", "ui.mode": "MODALITÀ INTERFACCIA", "ui.screensaver": "SALVASCHERMO", "ui.quick_system_select": "CAMBIO RAPIDO SISTEMA", "ui.transition_style": "STILE TRANSIZIONE", "ui.theme_manager": "GESTIONE TEMI", "ui.theme_set": "TEMA", "ui.on_screen_help": "AIUTO SU SCHERMO",
        "theme.info": "Installa o elimina temi. Simple Dark è incluso nell’app; gli altri temi vengono scaricati dai repository ufficiali RetroPie.", "theme.install_failed": "Installazione del tema non riuscita.\n\n", "theme.installed_apply": " è stato installato.\nApplicare questo tema ora?", "theme.delete_question": "Eliminare questo tema?", "theme.deleted": "Tema eliminato.", "theme.delete_failed": "Impossibile eliminare il tema.\n\n",
        "quit.really_quit_es": "USCIRE DAVVERO DA EMULATIONSTATION?", "quit.really_restart": "RIAVVIARE DAVVERO?", "quit.restart_es": "RIAVVIA EMULATIONSTATION", "quit.really_quit": "USCIRE DAVVERO?", "quit.quit_es": "ESCI DA EMULATIONSTATION"
    },
    "nl": {
        "common.open": "openen", "common.back": "terug", "common.yes": "JA", "common.no": "NEE", "common.ok": "OK", "common.delete": "VERWIJDEREN", "common.cancel": "ANNULEREN", "common.installed_suffix": " (geïnstalleerd)",
        "menu.main": "HOOFDMENU", "menu.games_systems": "SPELLEN & SYSTEMEN", "menu.scraper": "SPELINFORMATIE", "menu.sound_settings": "GELUIDSINSTELLINGEN", "menu.ui_settings": "INTERFACE", "menu.collections": "SPELCOLLECTIES", "menu.other_settings": "OVERIGE INSTELLINGEN", "menu.configure_input": "BESTURING INSTELLEN", "menu.quit": "AFSLUITEN",
        "games.select_folder": "KIES SPELMAP", "games.select_this_folder": "KIES DEZE MAP", "games.use_this_directory": "deze map gebruiken", "games.game_folder": "SPELMAP", "games.save_error": "De systeemconfiguratie kon niet worden opgeslagen.",
        "scraper.source": "BRON", "scraper.language": "SCRAPER-TAAL", "scraper.language_label": "TAAL (SCREENSCRAPER)", "scraper.region": "SCRAPER-REGIO", "scraper.region_label": "REGIO (SCREENSCRAPER)", "scraper.ratings": "BEOORDELINGEN DOWNLOADEN", "scraper.now": "NU DOWNLOADEN",
        "region.europe": "Europa", "region.japan": "Japan", "region.world": "Wereld",
        "sound.system_volume": "SYSTEEMVOLUME", "sound.navigation_sounds": "NAVIGATIEGELUIDEN", "sound.video_audio": "VIDEOAUDIO",
        "ui.language": "TAAL", "ui.mode": "INTERFACEMODUS", "ui.screensaver": "SCHERMBEVEILIGING", "ui.quick_system_select": "SNEL VAN SYSTEEM WISSELEN", "ui.transition_style": "OVERGANGSSTIJL", "ui.theme_manager": "THEMABEHEER", "ui.theme_set": "THEMA", "ui.on_screen_help": "HULP OP SCHERM",
        "theme.info": "Installeer of verwijder thema’s. Simple Dark wordt met de app meegeleverd; andere thema’s worden uit de officiële RetroPie-repositories gedownload.", "theme.install_failed": "Installatie van thema mislukt.\n\n", "theme.installed_apply": " is geïnstalleerd.\nDit thema nu toepassen?", "theme.delete_question": "Dit thema verwijderen?", "theme.deleted": "Thema verwijderd.", "theme.delete_failed": "Thema kon niet worden verwijderd.\n\n",
        "quit.really_quit_es": "EMULATIONSTATION ECHT AFSLUITEN?", "quit.really_restart": "ECHT HERSTARTEN?", "quit.restart_es": "EMULATIONSTATION HERSTARTEN", "quit.really_quit": "ECHT AFSLUITEN?", "quit.quit_es": "EMULATIONSTATION AFSLUITEN"
    },
    "pt": {
        "common.open": "abrir", "common.back": "voltar", "common.yes": "SIM", "common.no": "NÃO", "common.ok": "OK", "common.delete": "ELIMINAR", "common.cancel": "CANCELAR", "common.installed_suffix": " (instalado)",
        "menu.main": "MENU PRINCIPAL", "menu.games_systems": "JOGOS E SISTEMAS", "menu.scraper": "INFORMAÇÕES DOS JOGOS", "menu.sound_settings": "DEFINIÇÕES DE SOM", "menu.ui_settings": "INTERFACE", "menu.collections": "COLEÇÕES DE JOGOS", "menu.other_settings": "OUTRAS DEFINIÇÕES", "menu.configure_input": "CONFIGURAR CONTROLOS", "menu.quit": "SAIR",
        "games.select_folder": "ESCOLHER PASTA DE JOGOS", "games.select_this_folder": "ESCOLHER ESTA PASTA", "games.use_this_directory": "usar esta pasta", "games.game_folder": "PASTA DE JOGOS", "games.save_error": "Não foi possível guardar a configuração dos sistemas.",
        "scraper.source": "FONTE", "scraper.language": "IDIOMA DO SCRAPER", "scraper.language_label": "IDIOMA (SCREENSCRAPER)", "scraper.region": "REGIÃO DO SCRAPER", "scraper.region_label": "REGIÃO (SCREENSCRAPER)", "scraper.ratings": "TRANSFERIR AVALIAÇÕES", "scraper.now": "TRANSFERIR AGORA",
        "region.europe": "Europa", "region.japan": "Japão", "region.world": "Mundo",
        "sound.system_volume": "VOLUME DO SISTEMA", "sound.navigation_sounds": "SONS DE NAVEGAÇÃO", "sound.video_audio": "ÁUDIO DE VÍDEO",
        "ui.language": "IDIOMA", "ui.mode": "MODO DA INTERFACE", "ui.screensaver": "PROTEÇÃO DE ECRÃ", "ui.quick_system_select": "TROCA RÁPIDA DE SISTEMA", "ui.transition_style": "ESTILO DE TRANSIÇÃO", "ui.theme_manager": "GESTOR DE TEMAS", "ui.theme_set": "TEMA", "ui.on_screen_help": "AJUDA NO ECRÃ",
        "theme.info": "Instale ou elimine temas. Simple Dark está incluído na aplicação; os outros temas são transferidos dos repositórios oficiais do RetroPie.", "theme.install_failed": "Falha ao instalar o tema.\n\n", "theme.installed_apply": " foi instalado.\nAplicar este tema agora?", "theme.delete_question": "Eliminar este tema?", "theme.deleted": "Tema eliminado.", "theme.delete_failed": "Não foi possível eliminar o tema.\n\n",
        "quit.really_quit_es": "SAIR MESMO DO EMULATIONSTATION?", "quit.really_restart": "REINICIAR MESMO?", "quit.restart_es": "REINICIAR EMULATIONSTATION", "quit.really_quit": "SAIR MESMO?", "quit.quit_es": "SAIR DO EMULATIONSTATION"
    },
    "pl": {
        "common.open": "otwórz", "common.back": "wstecz", "common.yes": "TAK", "common.no": "NIE", "common.ok": "OK", "common.delete": "USUŃ", "common.cancel": "ANULUJ", "common.installed_suffix": " (zainstalowany)",
        "menu.main": "MENU GŁÓWNE", "menu.games_systems": "GRY I SYSTEMY", "menu.scraper": "INFORMACJE O GRACH", "menu.sound_settings": "USTAWIENIA DŹWIĘKU", "menu.ui_settings": "INTERFEJS", "menu.collections": "KOLEKCJE GIER", "menu.other_settings": "INNE USTAWIENIA", "menu.configure_input": "KONFIGURUJ STEROWANIE", "menu.quit": "WYJDŹ",
        "games.select_folder": "WYBIERZ FOLDER GIER", "games.select_this_folder": "WYBIERZ TEN FOLDER", "games.use_this_directory": "użyj tego folderu", "games.game_folder": "FOLDER GIER", "games.save_error": "Nie udało się zapisać konfiguracji systemów.",
        "scraper.source": "ŹRÓDŁO", "scraper.language": "JĘZYK SCRAPERA", "scraper.language_label": "JĘZYK (SCREENSCRAPER)", "scraper.region": "REGION SCRAPERA", "scraper.region_label": "REGION (SCREENSCRAPER)", "scraper.ratings": "POBIERZ OCENY", "scraper.now": "POBIERZ TERAZ",
        "region.europe": "Europa", "region.japan": "Japonia", "region.world": "Świat",
        "sound.system_volume": "GŁOŚNOŚĆ SYSTEMU", "sound.navigation_sounds": "DŹWIĘKI NAWIGACJI", "sound.video_audio": "DŹWIĘK WIDEO",
        "ui.language": "JĘZYK", "ui.mode": "TRYB INTERFEJSU", "ui.screensaver": "WYGASZACZ EKRANU", "ui.quick_system_select": "SZYBKA ZMIANA SYSTEMU", "ui.transition_style": "STYL PRZEJŚCIA", "ui.theme_manager": "MENEDŻER MOTYWÓW", "ui.theme_set": "MOTYW", "ui.on_screen_help": "POMOC NA EKRANIE",
        "theme.info": "Instaluj lub usuwaj motywy. Simple Dark jest dołączony do aplikacji; pozostałe motywy są pobierane z oficjalnych repozytoriów RetroPie.", "theme.install_failed": "Instalacja motywu nie powiodła się.\n\n", "theme.installed_apply": " został zainstalowany.\nZastosować ten motyw teraz?", "theme.delete_question": "Usunąć ten motyw?", "theme.deleted": "Motyw usunięty.", "theme.delete_failed": "Nie udało się usunąć motywu.\n\n",
        "quit.really_quit_es": "NAPRAWDĘ WYJŚĆ Z EMULATIONSTATION?", "quit.really_restart": "NAPRAWDĘ URUCHOMIĆ PONOWNIE?", "quit.restart_es": "URUCHOM PONOWNIE EMULATIONSTATION", "quit.really_quit": "NAPRAWDĘ WYJŚĆ?", "quit.quit_es": "WYJDŹ Z EMULATIONSTATION"
    }
}

# Missing non-English strings intentionally fall back through en.json. Keep the
# files sparse instead of duplicating English text.
i18n = ROOT / "resources" / "i18n"
i18n.mkdir(parents=True, exist_ok=True)
for code, values in languages.items():
    (i18n / f"{code}.json").write_text(json.dumps(values, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

localization_header = r'''#pragma once
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
'''
(ROOT / "es-core/src/WebOSLocalization.h").write_text(localization_header)

manager_header = r'''#pragma once
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
'''
(ROOT / "es-app/src/WebOSThemeManager.h").write_text(manager_header)

manager_cpp = r'''#include "WebOSThemeManager.h"

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

    const std::string bundled = "resources/bundled-themes/simple-dark.zip";
    if(std::string(theme.folderName) == "simple-dark" && Utils::FileSystem::isRegularFile(bundled))
        return extractTheme(bundled, theme, error);

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
        return true;

    const WebOSThemeEntry* simpleDark = nullptr;
    for(const auto& theme : sThemes)
        if(std::string(theme.folderName) == "simple-dark")
            simpleDark = &theme;
    if(!simpleDark)
        return false;

    if(!webosThemeInstalled(*simpleDark))
    {
        if(!Utils::FileSystem::isRegularFile("resources/bundled-themes/simple-dark.zip"))
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
    return true;
}
#endif
'''
(ROOT / "es-app/src/WebOSThemeManager.cpp").write_text(manager_cpp)

# CMake: compile the new manager only as part of the app target.
cmake = ROOT / "es-app/CMakeLists.txt"
text = cmake.read_text()
if "src/WebOSThemeManager.h" not in text:
    text = text.replace("    ${CMAKE_CURRENT_SOURCE_DIR}/src/CollectionSystemManager.h\n", "    ${CMAKE_CURRENT_SOURCE_DIR}/src/CollectionSystemManager.h\n    ${CMAKE_CURRENT_SOURCE_DIR}/src/WebOSThemeManager.h\n")
if "src/WebOSThemeManager.cpp" not in text:
    text = text.replace("    ${CMAKE_CURRENT_SOURCE_DIR}/src/CollectionSystemManager.cpp\n", "    ${CMAKE_CURRENT_SOURCE_DIR}/src/CollectionSystemManager.cpp\n    ${CMAKE_CURRENT_SOURCE_DIR}/src/WebOSThemeManager.cpp\n")
cmake.write_text(text)

settings = ROOT / "es-core/src/Settings.cpp"
text = settings.read_text()
if "WebOSBundledSimpleDarkSeeded" not in text:
    text = text.replace('mStringMap["WebOSScraperRegion"] = "eu";\n', 'mStringMap["WebOSScraperRegion"] = "eu";\n\tmBoolMap["WebOSBundledSimpleDarkSeeded"] = false;\n')
settings.write_text(text)

# Main: seed the bundled default once before views/themes are initialized.
main = ROOT / "es-app/src/main.cpp"
text = main.read_text()
if '#include "WebOSThemeManager.h"' not in text:
    text = text.replace('#include "SystemScreenSaver.h"\n', '#include "SystemScreenSaver.h"\n#ifdef WEBOS\n#include "WebOSThemeManager.h"\n#endif\n')
seed = '''\n#ifdef WEBOS\n\tstd::string bundledThemeError;\n\tif(!webosEnsureBundledDefaultTheme(bundledThemeError))\n\t\tLOG(LogWarning) << "Could not initialize bundled Simple Dark theme: " << bundledThemeError;\n#endif\n'''
if "webosEnsureBundledDefaultTheme" not in text:
    text = text.replace('\tatexit(&onExit);\n', '\tatexit(&onExit);\n' + seed)
main.write_text(text)

# Convert a focused first set of existing webOS labels to stable keys.
def keyed(path: Path, replacements: list[tuple[str, str, str]]) -> None:
    text = path.read_text()
    for english, german, key in replacements:
        pattern = re.compile(r'webosTrLegacy\(\s*"' + re.escape(english) + r'"\s*,\s*"' + re.escape(german) + r'"\s*\)')
        text = pattern.sub(f'webosTr("{key}", "{english}")', text)
    path.write_text(text)

gui = ROOT / "es-app/src/guis/GuiMenu.cpp"
text = gui.read_text()
text = text.replace('#include "WebOSLocalization.h"\n#ifdef WEBOS\n#include <curl/curl.h>\n#include <zip.h>\n#include <cstdio>\n#endif', '#include "WebOSLocalization.h"\n#ifdef WEBOS\n#include "WebOSThemeManager.h"\n#endif')
start = text.find('#ifdef WEBOS\nstruct WebOSThemeEntry')
end_marker = '#endif\n\nGuiMenu::GuiMenu'
end = text.find(end_marker, start)
if start != -1 and end != -1:
    text = text[:start] + 'GuiMenu::GuiMenu' + text[end + len(end_marker):]
gui.write_text(text)

pairs = [
    ("open", "öffnen", "common.open"), ("back", "zurück", "common.back"),
    ("SELECT GAME FOLDER", "SPIELEORDNER WÄHLEN", "games.select_folder"),
    ("SELECT THIS FOLDER", "DIESEN ORDNER WÄHLEN", "games.select_this_folder"),
    ("use this directory", "diesen Ordner verwenden", "games.use_this_directory"),
    ("MAIN MENU", "HAUPTMENÜ", "menu.main"), ("GAMES & SYSTEMS", "SPIELE & SYSTEME", "menu.games_systems"),
    ("SCRAPER", "SPIELINFORMATIONEN", "menu.scraper"), ("SOUND SETTINGS", "TONEINSTELLUNGEN", "menu.sound_settings"),
    ("UI SETTINGS", "OBERFLÄCHE", "menu.ui_settings"), ("GAME COLLECTION SETTINGS", "SPIELESAMMLUNGEN", "menu.collections"),
    ("OTHER SETTINGS", "WEITERE EINSTELLUNGEN", "menu.other_settings"), ("CONFIGURE INPUT", "STEUERUNG EINRICHTEN", "menu.configure_input"),
    ("QUIT", "BEENDEN", "menu.quit"), ("SCRAPE FROM", "DATENQUELLE", "scraper.source"),
    ("SCRAPER LANGUAGE", "SCRAPER-SPRACHE", "scraper.language"), ("LANGUAGE (SCREENSCRAPER)", "SPRACHE (SCREENSCRAPER)", "scraper.language_label"),
    ("SCRAPER REGION", "SCRAPER-REGION", "scraper.region"), ("REGION (SCREENSCRAPER)", "REGION (SCREENSCRAPER)", "scraper.region_label"),
    ("SCRAPE RATINGS", "BEWERTUNGEN LADEN", "scraper.ratings"), ("SCRAPE NOW", "JETZT LADEN", "scraper.now"),
    ("Europe", "Europa", "region.europe"), ("Japan", "Japan", "region.japan"), ("World", "Welt", "region.world"),
    ("GAME FOLDER", "SPIELEORDNER", "games.game_folder"), ("Could not save the systems configuration.", "Systemkonfiguration konnte nicht gespeichert werden.", "games.save_error"),
    ("SYSTEM VOLUME", "SYSTEMLAUTSTÄRKE", "sound.system_volume"), ("ENABLE NAVIGATION SOUNDS", "NAVIGATIONSTÖNE", "sound.navigation_sounds"),
    ("ENABLE VIDEO AUDIO", "VIDEO-TON", "sound.video_audio"), ("LANGUAGE", "SPRACHE", "ui.language"),
    ("UI MODE", "UI-MODUS", "ui.mode"), ("SCREENSAVER SETTINGS", "BILDSCHIRMSCHONER", "ui.screensaver"),
    ("QUICK SYSTEM SELECT", "SCHNELLER SYSTEMWECHSEL", "ui.quick_system_select"), ("TRANSITION STYLE", "ÜBERGANG", "ui.transition_style"),
    ("DOWNLOAD THEMES", "THEMES HERUNTERLADEN", "ui.theme_manager"), ("THEME SET", "DESIGN", "ui.theme_set"),
    ("ON-SCREEN HELP", "TASTENHINWEISE", "ui.on_screen_help"), ("YES", "JA", "common.yes"), ("NO", "NEIN", "common.no")
]
keyed(gui, pairs)

text = gui.read_text()
# Long games information call is split over lines, so replace it explicitly.
text = text.replace('webosTrLegacy("Enable a system and set its game folder. Changes are saved when you go back; restart EmulationStation to rescan games.",\n\t\t\t"System aktivieren und Spieleordner setzen. Beim Zurückgehen wird gespeichert; danach EmulationStation neu starten.")', 'webosTr("games.info", "Enable a system and set its game folder. Changes are saved when you go back; restart EmulationStation to rescan games.")')

# Replace the old two-language selector with the centralized language list.
lang_pattern = re.compile(r'#ifdef WEBOS\n\tauto language = std::make_shared<OptionListComponent<std::string>>\(mWindow, .*?\n#endif', re.S)
lang_block = '''#ifdef WEBOS
\tauto language = std::make_shared<OptionListComponent<std::string>>(mWindow, webosTr("ui.language", "LANGUAGE"), false);
\tconst std::string currentLanguage = webosCurrentLanguage();
\tfor(const auto& entry : webosLanguages())
\t\tlanguage->add(entry.nativeName, entry.code, currentLanguage == entry.code);
\ts->addWithLabel(webosTr("ui.language", "LANGUAGE"), language);
\ts->addSaveFunc([language] { Settings::getInstance()->setString("WebOSLanguage", language->getSelected()); });
#endif'''
text, count = lang_pattern.subn(lang_block, text, count=1)
if count != 1:
    raise SystemExit("Could not replace webOS language selector")

# Replace the complete theme UI with install/delete behavior.
manager_start = text.find('#ifdef WEBOS\nvoid GuiMenu::openWebOSThemeManager()')
manager_end = text.find('#endif\n\nvoid GuiMenu::openOtherSettings()', manager_start)
if manager_start == -1 or manager_end == -1:
    raise SystemExit("Could not locate theme manager function")
manager_function = r'''#ifdef WEBOS
void GuiMenu::openWebOSThemeManager()
{
    auto s = new GuiSettings(mWindow, webosTr("ui.theme_manager", "THEME MANAGER"));

    ComponentListRow infoRow;
    infoRow.addElement(std::make_shared<TextComponent>(mWindow,
        webosTr("theme.info", "Install or remove themes. Simple Dark is included with the app; other themes are downloaded from the official RetroPie repositories."),
        Font::get(FONT_SIZE_SMALL), 0x777777FF), true);
    s->addRow(infoRow);

    for(const auto& theme : webosThemes())
    {
        const bool installed = webosThemeInstalled(theme);
        std::string label = theme.displayName;
        if(installed)
            label += webosTr("common.installed_suffix", " (installed)");

        ComponentListRow row;
        row.addElement(std::make_shared<TextComponent>(mWindow, label, Font::get(FONT_SIZE_MEDIUM), 0x777777FF), true);
        row.addElement(makeArrow(mWindow), false);
        if(installed)
        {
            row.makeAcceptInputHandler([this, theme] {
                mWindow->pushGui(new GuiMsgBox(mWindow,
                    std::string(webosTr("theme.delete_question", "Delete this theme?")) + "\n\n" + theme.displayName,
                    webosTr("common.delete", "DELETE"), [this, theme] {
                        std::string error;
                        std::string replacementTheme;
                        bool activeThemeChanged = false;
                        if(!webosDeleteTheme(theme, error, activeThemeChanged, replacementTheme))
                        {
                            mWindow->pushGui(new GuiMsgBox(mWindow,
                                std::string(webosTr("theme.delete_failed", "Theme could not be deleted.\n\n")) + error));
                            return;
                        }

                        if(activeThemeChanged)
                        {
                            Scripting::fireEvent("theme-changed", replacementTheme, theme.folderName);
                            CollectionSystemManager::get()->updateSystemsList();
                            ViewController::get()->reloadAll(true);
                        }
                        mWindow->pushGui(new GuiMsgBox(mWindow, webosTr("theme.deleted", "Theme deleted."), webosTr("common.ok", "OK")));
                    }, webosTr("common.cancel", "CANCEL"), nullptr));
            });
        }
        else
        {
            row.makeAcceptInputHandler([this, theme] {
                std::string error;
                LOG(LogInfo) << "webOS theme manager: installing " << theme.displayName;
                if(!webosInstallTheme(theme, error))
                {
                    mWindow->pushGui(new GuiMsgBox(mWindow,
                        std::string(webosTr("theme.install_failed", "Theme installation failed.\n\n")) + error));
                    return;
                }

                mWindow->pushGui(new GuiMsgBox(mWindow,
                    std::string(theme.displayName) + webosTr("theme.installed_apply", " was installed.\nApply this theme now?"),
                    webosTr("common.yes", "YES"), [theme] {
                        const std::string oldTheme = Settings::getInstance()->getString("ThemeSet");
                        Settings::getInstance()->setString("ThemeSet", theme.folderName);
                        Settings::getInstance()->saveFile();
                        Scripting::fireEvent("theme-changed", theme.folderName, oldTheme);
                        CollectionSystemManager::get()->updateSystemsList();
                        ViewController::get()->reloadAll(true);
                    }, webosTr("common.no", "NO"), nullptr));
            });
        }
        s->addRow(row);
    }

    mWindow->pushGui(s);
}
#endif

void GuiMenu::openOtherSettings()'''
text = text[:manager_start] + manager_function + text[manager_end + len('#endif\n\nvoid GuiMenu::openOtherSettings()'):]
gui.write_text(text)

# Root Back confirmation also uses translation keys now.
system_view = ROOT / "es-app/src/views/SystemView.cpp"
keyed(system_view, [
    ("REALLY QUIT EMULATIONSTATION?", "EMULATIONSTATION WIRKLICH BEENDEN?", "quit.really_quit_es"),
    ("YES", "JA", "common.yes"), ("NO", "NEIN", "common.no")
])

# Key the webOS quit menu without changing the non-webOS path.
text = gui.read_text()
text = text.replace('new GuiSettings(mWindow, webosTrLegacy("QUIT", "BEENDEN"))', 'new GuiSettings(mWindow, webosTr("menu.quit", "QUIT"))')
text = text.replace('new GuiMsgBox(window, "REALLY RESTART?", "YES", restart_es_fx, "NO", nullptr)', 'new GuiMsgBox(window, webosTr("quit.really_restart", "REALLY RESTART?"), webosTr("common.yes", "YES"), restart_es_fx, webosTr("common.no", "NO"), nullptr)')
text = text.replace('std::make_shared<TextComponent>(window, "RESTART EMULATIONSTATION",', 'std::make_shared<TextComponent>(window, webosTr("quit.restart_es", "RESTART EMULATIONSTATION"),')
text = text.replace('new GuiMsgBox(window, "REALLY QUIT?", "YES", quit_es_fx, "NO", nullptr)', 'new GuiMsgBox(window, webosTr("quit.really_quit", "REALLY QUIT?"), webosTr("common.yes", "YES"), quit_es_fx, webosTr("common.no", "NO"), nullptr)')
text = text.replace('std::make_shared<TextComponent>(window, "QUIT EMULATIONSTATION",', 'std::make_shared<TextComponent>(window, webosTr("quit.quit_es", "QUIT EMULATIONSTATION"),')
gui.write_text(text)

# Bundle the pinned Simple Dark archive in the app resources. It is extracted
# once into the writable user theme directory, so deleting it later is durable.
bundle_dir = ROOT / "resources/bundled-themes"
bundle_dir.mkdir(parents=True, exist_ok=True)
archive = bundle_dir / "simple-dark.zip"
url = "https://codeload.github.com/RetroPie/es-theme-simple-dark/zip/058472cfbc3b4fe9ddf1ab452908fab40e32d29c"
with urllib.request.urlopen(url, timeout=120) as response, archive.open("wb") as output:
    shutil.copyfileobj(response, output)
with zipfile.ZipFile(archive) as zf:
    if zf.testzip() is not None:
        raise SystemExit("Bundled Simple Dark archive failed ZIP validation")

# Document the new structure briefly.
readme = ROOT / "README.md"
text = readme.read_text()
text = text.replace("- built-in webOS-oriented UI text/localization and theme management", "- keyed JSON localization with English fallback and eight selectable UI languages\n- theme manager with install/remove support; Simple Dark is bundled as the first-run default")
if "## Localization" not in text:
    marker = "## Runtime log\n"
    section = '''## Localization

webOS UI translations use stable keys from `WebOSLocalization.h` and flat JSON files in `resources/i18n/`. English is the fallback language when a key is missing. The initial language set is German, English, French, Spanish, Italian, Dutch, Portuguese and Polish.

## Themes

`Simple Dark` is bundled in the IPK and installed into the writable user theme directory on first run. It is the default for new installations, but it is not protected: deleting it from the theme manager keeps it deleted. The bundled archive remains available for an explicit reinstall.

'''
    text = text.replace(marker, section + marker)
readme.write_text(text)

# Sanity checks and remove this one-shot migration script from the resulting tree.
assert 'webosTr("menu.main", "MAIN MENU")' in gui.read_text()
assert 'webosDeleteTheme' in gui.read_text()
assert 'webosEnsureBundledDefaultTheme' in main.read_text()
assert (ROOT / "resources/i18n/fr.json").is_file()
assert archive.stat().st_size > 100000
Path(__file__).unlink()
