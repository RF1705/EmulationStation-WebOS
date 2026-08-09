#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch-retropie-webos-theme-runtime.py <RetroPie EmulationStation source>")

path = Path(sys.argv[1]).resolve() / "es-app/src/guis/GuiMenu.cpp"
if not path.is_file():
    raise SystemExit(f"missing upstream file: {path}")

text = path.read_text()

# GitHub/codeload ZIPs contain explicit directory entries ending in '/'.
# RetroPie FileSystemUtil::createDirectory() normalizes the path for mkdir(),
# but stores the exists-cache result under the original, unnormalized string.
# Calling it first with "dir/" can therefore leave a cached false value for
# "dir"; the following file then sees the directory as missing and mkdir()
# fails with EEXIST. Ignore directory entries and create only the parent of
# actual files, always without a trailing slash.
old_directory_block = r'''		const std::string destination = destinationRoot + "/" + relative;
		if(relative.back() == '/')
		{
			if(!Utils::FileSystem::createDirectory(destination))
			{
				zip_close(archive);
				error = webosTr("Could not create theme directory.", "Theme-Verzeichnis konnte nicht erstellt werden.");
				return false;
			}
			continue;
		}
'''
new_directory_block = r'''		const std::string destination = destinationRoot + "/" + relative;
		if(relative.back() == '/')
			continue;
'''
if old_directory_block not in text:
    raise SystemExit("theme directory-entry extraction anchor not found")
text = text.replace(old_directory_block, new_directory_block, 1)

# If another filesystem problem ever occurs, include the exact path in both
# the UI error and the log instead of showing the same generic mkdir message.
old_parent_block = r'''		if(!Utils::FileSystem::createDirectory(Utils::FileSystem::getParent(destination)))
		{
			zip_close(archive);
			error = webosTr("Could not create theme directory.", "Theme-Verzeichnis konnte nicht erstellt werden.");
			return false;
		}
'''
new_parent_block = r'''		const std::string parentDirectory = Utils::FileSystem::getParent(destination);
		if(!Utils::FileSystem::createDirectory(parentDirectory))
		{
			zip_close(archive);
			error = std::string(webosTr("Could not create theme directory: ", "Theme-Verzeichnis konnte nicht erstellt werden: ")) + parentDirectory;
			LOG(LogError) << "webOS theme manager: mkdir failed: " << parentDirectory;
			return false;
		}
'''
if old_parent_block not in text:
    raise SystemExit("theme parent-directory extraction anchor not found")
text = text.replace(old_parent_block, new_parent_block, 1)

old_root_block = r'''	if(!Utils::FileSystem::createDirectory(configRoot + "/themes"))
	{
		error = webosTr("Theme directory could not be created.", "Theme-Verzeichnis konnte nicht erstellt werden.");
		return false;
	}
'''
new_root_block = r'''	const std::string themesRoot = configRoot + "/themes";
	if(!Utils::FileSystem::createDirectory(themesRoot))
	{
		error = std::string(webosTr("Theme directory could not be created: ", "Theme-Verzeichnis konnte nicht erstellt werden: ")) + themesRoot;
		LOG(LogError) << "webOS theme manager: mkdir failed: " << themesRoot;
		return false;
	}
'''
if old_root_block not in text:
    raise SystemExit("theme root-directory anchor not found")
text = text.replace(old_root_block, new_root_block, 1)

path.write_text(text)
print("Applied webOS theme extraction runtime fix")
