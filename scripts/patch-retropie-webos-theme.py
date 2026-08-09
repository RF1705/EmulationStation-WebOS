#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch-retropie-webos-theme.py <RetroPie EmulationStation source>")

path = Path(sys.argv[1]).resolve() / "es-core/src/ThemeData.cpp"
if not path.is_file():
    raise SystemExit(f"missing upstream file: {path}")

text = path.read_text()
old = '''\tstatic const size_t pathCount = 2;\n\tstd::string paths[pathCount] =\n\t{\n\t\t"/etc/emulationstation/themes",\n\t\tUtils::FileSystem::getHomePath() + "/.emulationstation/themes"\n\t};\n'''
new = '''#ifdef WEBOS\n\tstatic const size_t pathCount = 3;\n\tstd::string paths[pathCount] =\n\t{\n\t\t"/etc/emulationstation/themes",\n\t\tUtils::FileSystem::getHomePath() + "/.emulationstation/themes",\n\t\t"./themes"\n\t};\n#else\n\tstatic const size_t pathCount = 2;\n\tstd::string paths[pathCount] =\n\t{\n\t\t"/etc/emulationstation/themes",\n\t\tUtils::FileSystem::getHomePath() + "/.emulationstation/themes"\n\t};\n#endif\n'''
if old not in text:
    raise SystemExit("theme search path anchor not found")
text = text.replace(old, new, 1)
path.write_text(text)
print("Added bundled webOS theme search path")
