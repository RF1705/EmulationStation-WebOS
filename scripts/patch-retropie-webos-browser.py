#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch-retropie-webos-browser.py <RetroPie EmulationStation source>")

path = Path(sys.argv[1]).resolve() / "es-app/src/guis/GuiMenu.cpp"
if not path.is_file():
    raise SystemExit(f"missing upstream file: {path}")

text = path.read_text()

anchor = 'static bool saveWebOSSystemsConfig()\n'
browser = r'''static std::string webosNearestDirectory(std::string path)
{
	while(!path.empty() && !Utils::FileSystem::isDirectory(path))
	{
		const std::string parent = Utils::FileSystem::getParent(path);
		if(parent.empty() || parent == path)
			break;
		path = parent;
	}

	if(Utils::FileSystem::isDirectory(path))
		return path;

	const char* fallbacks[] = {
		"/media/developer/network-storage/games",
		"/media/developer/network-storage",
		"/media/developer",
		"/media",
		"/"
	};
	for(const char* fallback : fallbacks)
		if(Utils::FileSystem::isDirectory(fallback))
			return fallback;

	return "/";
}

class GuiDirectoryBrowser : public GuiComponent
{
public:
	typedef std::function<void(const std::string&)> SelectCallback;

	GuiDirectoryBrowser(Window* window, const std::string& initialPath, const SelectCallback& callback) :
		GuiComponent(window), mPath(webosNearestDirectory(initialPath)), mCallback(callback)
	{
		rebuild();
	}

	bool input(InputConfig* config, Input input) override
	{
		if(config->isMappedTo("b", input) && input.value != 0)
		{
			delete this;
			return true;
		}
		return GuiComponent::input(config, input);
	}

	std::vector<HelpPrompt> getHelpPrompts() override
	{
		std::vector<HelpPrompt> prompts;
		prompts.push_back(HelpPrompt("a", webosTr("open", "öffnen")));
		prompts.push_back(HelpPrompt("b", webosTr("back", "zurück")));
		return prompts;
	}

private:
	void addDirectory(const std::string& label, const std::string& target)
	{
		ComponentListRow row;
		row.addElement(std::make_shared<TextComponent>(mWindow, label, Font::get(FONT_SIZE_MEDIUM), 0x777777FF), true);
		row.addElement(makeArrow(mWindow), false);
		row.makeAcceptInputHandler([this, target] {
			mPath = webosNearestDirectory(target);
			rebuild();
		});
		mMenu->addRow(row);
	}

	void rebuild()
	{
		if(mMenu)
		{
			removeChild(mMenu.get());
			mMenu.reset();
		}

		mMenu.reset(new MenuComponent(mWindow, webosTr("SELECT GAME FOLDER", "SPIELEORDNER WÄHLEN")));
		addChild(mMenu.get());

		ComponentListRow currentRow;
		currentRow.addElement(std::make_shared<TextComponent>(mWindow, mPath, Font::get(FONT_SIZE_SMALL), 0x777777FF), true);
		mMenu->addRow(currentRow);

		const std::string parent = Utils::FileSystem::getParent(mPath);
		if(!parent.empty() && parent != mPath)
			addDirectory("..", parent);

		std::vector<std::string> directories;
		for(const std::string& entry : Utils::FileSystem::getDirContent(mPath, false))
		{
			if(Utils::FileSystem::isDirectory(entry) && !Utils::FileSystem::isHidden(entry))
				directories.push_back(entry);
		}
		std::sort(directories.begin(), directories.end());

		for(const std::string& directory : directories)
			addDirectory(Utils::FileSystem::getFileName(directory), directory);

		mMenu->addButton(webosTr("SELECT THIS FOLDER", "DIESEN ORDNER WÄHLEN"),
			webosTr("use this directory", "diesen Ordner verwenden"), [this] {
				mCallback(mPath);
				delete this;
			});

		setSize((float)Renderer::getScreenWidth(), (float)Renderer::getScreenHeight());
		mMenu->setPosition((mSize.x() - mMenu->getSize().x()) / 2, Renderer::getScreenHeight() * 0.08f);
	}

	std::unique_ptr<MenuComponent> mMenu;
	std::string mPath;
	SelectCallback mCallback;
};

'''
if 'class GuiDirectoryBrowser' not in text:
    if anchor not in text:
        raise SystemExit("directory browser insertion anchor not found")
    text = text.replace(anchor, browser + anchor, 1)

old = r'''		pathRow.makeAcceptInputHandler([this, pathText, pathKey, preset] {
			const std::string current = Settings::getInstance()->getString(pathKey);
			mWindow->pushGui(new GuiTextEditPopup(mWindow,
				preset.fullName,
				current,
				[pathText, pathKey](const std::string& value) {
					Settings::getInstance()->setString(pathKey, value);
					pathText->setText(value);
				}, false));
		});
'''
new = r'''		pathRow.makeAcceptInputHandler([this, pathText, pathKey] {
			const std::string current = Settings::getInstance()->getString(pathKey);
			mWindow->pushGui(new GuiDirectoryBrowser(mWindow, current,
				[pathText, pathKey](const std::string& value) {
					Settings::getInstance()->setString(pathKey, value);
					pathText->setText(value);
				}));
		});
'''
if old not in text:
    raise SystemExit("text path editor anchor not found")
text = text.replace(old, new, 1)

path.write_text(text)
print("Applied graphical webOS directory browser")
