# Upstream baseline

EmulationStation WebOS is based on the RetroPie fork of EmulationStation.

On 2026-08-09 the project switched from applying webOS patch scripts during CI to maintaining the complete application source directly in this repository.

- Upstream repository: `RetroPie/EmulationStation`
- Imported commit: `1071b8358b316ebda837933150db949bda90495e`
- Vendored pugixml revision: `ee86beb30e4973f5feffe3ce63bfa4fbadf72f38`
- Upstream license: MIT

The imported source was patched with the complete webOS patch set used by the previous CI build before being committed here. This preserves the behavior of the patch-based build while making future webOS work normal source changes.

## Comparing future upstream changes

Upstream is no longer fetched during normal builds. To inspect later RetroPie changes in a local clone:

```sh
git remote add retropie https://github.com/RetroPie/EmulationStation.git
git fetch retropie
```

Compare or cherry-pick individual upstream changes intentionally rather than automatically rebasing the webOS project.

`external/pugixml` is vendored rather than kept as a Git submodule; its own license files remain in that directory.
