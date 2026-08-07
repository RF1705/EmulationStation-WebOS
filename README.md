# EmulationStation for LG webOS

Experimental ARMv7 port of the RetroPie fork of EmulationStation for rooted LG webOS TVs.

This repository contains the webOS build, compatibility patches and IPK packaging. The EmulationStation source itself is fetched from upstream during CI and is currently pinned to:

- Upstream: `RetroPie/EmulationStation`
- Commit: `1071b8358b316ebda837933150db949bda90495e`
- Target: ARMv7 / Cortex-A9 / softfp / NEON
- Graphics: SDL-webOS + OpenGL ES 2
- Package ID: `com.rf1705.emulationstation`

## webOS-specific choices

The webOS build intentionally stays smaller than a normal desktop RetroPie build:

- no libVLC runtime; video widgets fall back to their static artwork
- no ALSA mixer integration; SDL/webOS owns application audio/input
- no Raspberry Pi-specific Broadcom/OMX code
- no ES-DE dependencies such as FFmpeg, ICU, Poppler, HarfBuzz or libgit2
- only the recursive shared-library dependency closure is included in the IPK
- all packaged ELF files are stripped

The first goal is a lightweight TV frontend that can later hand games off to native webOS ports such as ScummVM and RetroArch.

## Build

GitHub Actions builds the webOS IPK using:

- the `webosbrew/openlgtv` Buildroot SDK
- `webosbrew/SDL-webOS`
- a pinned vcpkg revision for the remaining libraries
- `ares-package` for IPK generation

Pushes to `main` automatically build an artifact named similar to:

```text
com.rf1705.emulationstation_1.0.0-webos0.1.0_arm.ipk
```

## Runtime log

The native launcher redirects stdout and stderr to:

```text
/tmp/com.rf1705.emulationstation.log
```

On a rooted TV this can be inspected with:

```sh
cat /tmp/com.rf1705.emulationstation.log
```

## Status

Work in progress. Build and packaging are being adapted from the previously proven webOS ARM toolchain; input mapping, Magic Remote integration and automatic system/game configuration are subsequent porting steps.
