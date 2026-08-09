# EmulationStation WebOS

A TV-focused EmulationStation frontend for rooted LG webOS TVs, based on the RetroPie fork of EmulationStation.

This repository contains the EmulationStation application source directly. CI no longer downloads and patches `RetroPie/EmulationStation` for every build; webOS is maintained as a first-class target in this codebase.

- Target: LG webOS, ARMv7 / Cortex-A9 / softfp / NEON
- Graphics/input: SDL-webOS + OpenGL ES 2
- Package ID: `com.rf1705.emulationstation`
- Upstream baseline: `RetroPie/EmulationStation` commit `1071b8358b316ebda837933150db949bda90495e`
- License: MIT

## webOS integration

The port is intentionally TV-native rather than a Raspberry Pi environment transplanted onto a TV.

- LG Magic Remote navigation and OK input
- Back is claimed from webOS and mapped to EmulationStation back/escape behavior
- Home is claimed as the EmulationStation menu key while the webOS Home ribbon is suppressed inside the app
- root-level Back asks before cleanly exiting EmulationStation
- host shutdown/reboot actions are removed from the quit menu
- graphical Games & Systems configuration for webOS paths
- no artificial `webos` console/system entry in the carousel
- a zero-system installation opens configuration instead of failing with the desktop EmulationStation error
- keyed JSON localization with English fallback and eight selectable UI languages
- theme manager with install/remove support; Simple Dark is bundled as the first-run default
- webOS file browser and scraper adaptations

## Source layout

The EmulationStation application sources live directly in this repository:

```text
es-app/
es-core/
external/
resources/
CMake/
CMakeLists.txt
```

`external/pugixml` is vendored as normal source files from the revision used by the imported upstream baseline. The previous `patch-retropie-webos-*.py` layer is gone.

See [`UPSTREAM.md`](UPSTREAM.md) for the exact baseline and how to compare future RetroPie changes manually.

## Build

GitHub Actions builds this source tree directly using the `openlgtv/buildroot-nc4` webOS Buildroot SDK, `webosbrew/SDL-webOS`, pinned vcpkg dependencies and `ares-package` for IPK generation.

Pushes to `main` build an artifact similar to:

```text
com.rf1705.emulationstation_1.0.0-webos0.1.0_arm.ipk
```

The webOS build deliberately omits Raspberry Pi-specific Broadcom/OMX code and the libVLC runtime. Packaged ELF files are stripped and only the required shared-library dependency closure is included.

## Localization

webOS UI translations use stable keys from `WebOSLocalization.h` and flat JSON files in `resources/i18n/`. English is the fallback language when a key is missing. The initial language set is German, English, French, Spanish, Italian, Dutch, Portuguese and Polish.

## Themes

`Simple Dark` is bundled in the IPK and installed into the writable user theme directory on first run. It is the default for new installations, but it is not protected: deleting it from the theme manager keeps it deleted. The bundled archive remains available for an explicit reinstall.

## Runtime log

The native launcher redirects stdout and stderr to:

```text
/tmp/com.rf1705.emulationstation.log
```

On a rooted TV:

```sh
cat /tmp/com.rf1705.emulationstation.log
```

## Project status

This is an active webOS fork and still a work in progress. The source history and architecture originate from EmulationStation and the RetroPie fork, while webOS-specific behavior is maintained here directly.

## Support

If this project is useful to you, you can support development on [Buy Me a Coffee](https://buymeacoffee.com/rf1705).

GitHub funding metadata is available in [`.github/FUNDING.yml`](.github/FUNDING.yml).
