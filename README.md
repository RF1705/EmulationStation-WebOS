# ES-DE for LG webOS

Experimental ARMv7 port of [ES-DE Frontend](https://gitlab.com/es-de/emulationstation-de) for LG webOS TVs.

The repository contains only the webOS-specific build and packaging layer. The upstream ES-DE source is checked out during GitHub Actions, cross-compiled with the webOSbrew ARM toolchain and packaged as an IPK.

## Status

The initial port focuses on producing a reproducible native package:

- ES-DE 3.4.1, pinned by tag
- ARMv7 / Cortex-A9 / softfp
- SDL-webOS and OpenGL ES
- build performed entirely by GitHub Actions
- webOS native-app wrapper and IPK packaging
- CI artifacts for every push and pull request
- release assets when a matching tag is pushed

Game launching is a separate porting step. Vanilla ES-DE executes emulator command lines, while a rootless webOS setup needs application-manager based hand-off to patched RetroArch and ScummVM packages.

## GitHub Actions

The `Build webOS IPK` workflow:

1. checks out ES-DE from GitLab;
2. downloads the webOSbrew SDK, SDL-webOS and `ares-package`;
3. cross-builds the required libraries;
4. builds ES-DE with GLES enabled;
5. stages the installed resources and runtime libraries;
6. creates an ARM IPK, checksum and Homebrew Channel manifest.

The dependency and SDK directories are cached between builds.

A manual run can select another ES-DE tag or commit using the `esde_ref` workflow input.

## Releases

Normal pushes create downloadable workflow artifacts. To publish a GitHub release, push a tag matching:

```text
esde_<version>_webos_<revision>
```

Example:

```bash
git tag esde_3.4.1_webos_0.1.0
git push origin esde_3.4.1_webos_0.1.0
```

## Installation

After a successful workflow run, download the IPK artifact and install it using the webOS CLI or the Homebrew Channel development tools.

```bash
ares-install com.rf1705.esde_3.4.1-webos0.1.0_arm.ipk
```

The package is currently intended for development and testing. A successful CI build proves that the binary and package were created; actual TV compatibility still needs device testing.

## Upstream and licensing

ES-DE is developed by the ES-DE project and is fetched unmodified before the webOS build adjustments are applied. This repository contains only the porting and packaging code. See the upstream project for its license and third-party notices.
