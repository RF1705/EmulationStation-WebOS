#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch-retropie-webos.py <RetroPie EmulationStation source>")

root = Path(sys.argv[1]).resolve()
cmake = root / "CMakeLists.txt"
volume_h = root / "es-app/src/VolumeControl.h"
volume_cpp = root / "es-app/src/VolumeControl.cpp"
main_cpp = root / "es-app/src/main.cpp"
input_manager = root / "es-core/src/InputManager.cpp"
vlc_cpp = root / "es-core/src/components/VideoVlcComponent.cpp"

for path in (cmake, volume_h, volume_cpp, main_cpp, input_manager, vlc_cpp):
    if not path.is_file():
        raise SystemExit(f"missing upstream file: {path}")

text = cmake.read_text()

option_anchor = 'option(CEC "Set to ON to enable CEC" ${CEC})\n'
if 'option(WEBOS "Build for LG webOS"' not in text:
    if option_anchor not in text:
        raise SystemExit("could not find CMake option anchor")
    text = text.replace(
        option_anchor,
        option_anchor + 'option(WEBOS "Build for LG webOS" ${WEBOS})\n',
        1,
    )

vlc_anchor = "find_package(VLC REQUIRED)"
if vlc_anchor in text:
    text = text.replace(
        vlc_anchor,
        "if(NOT WEBOS)\n    find_package(VLC REQUIRED)\nendif()",
        1,
    )
elif "if(NOT WEBOS)\n    find_package(VLC REQUIRED)\nendif()" not in text:
    raise SystemExit("could not find VLC dependency in CMakeLists.txt")

text = text.replace(
    'if(${CMAKE_SYSTEM_NAME} MATCHES "Linux")',
    'if(${CMAKE_SYSTEM_NAME} MATCHES "Linux" AND NOT WEBOS)',
)

project_anchor = "project(emulationstation-all)\n"
if "add_definitions(-DWEBOS)" not in text:
    if project_anchor not in text:
        raise SystemExit("could not find CMake project anchor")
    text = text.replace(
        project_anchor,
        project_anchor + "\nif(WEBOS)\n    add_definitions(-DWEBOS)\nendif()\n",
        1,
    )

cmake.write_text(text)

# webOS is Linux at the compiler level, but its application audio is provided
# by SDL/webOS. Do not pull the desktop ALSA mixer API into the frontend.
for path in (volume_h, volume_cpp):
    text = path.read_text()
    text = text.replace(
        "defined(__linux__)",
        "defined(__linux__) && !defined(WEBOS)",
    )
    path.write_text(text)

# A TV app must be usable before a controller has been configured. On webOS,
# fall back to RetroPie's own keyboard defaults immediately. SDL-webOS exposes
# the remote directional/OK keys as keyboard input; pointer clicks and the wheel
# are additionally translated into the same navigation inputs.
text = input_manager.read_text()
keyboard_anchor = (
    '\tmKeyboardInputConfig = new InputConfig(DEVICE_KEYBOARD, "Keyboard", KEYBOARD_GUID_STRING);\n'
    '\tloadInputConfig(mKeyboardInputConfig);\n'
)
keyboard_replacement = (
    '\tmKeyboardInputConfig = new InputConfig(DEVICE_KEYBOARD, "Keyboard", KEYBOARD_GUID_STRING);\n'
    '#ifdef WEBOS\n'
    '\tif(!loadInputConfig(mKeyboardInputConfig))\n'
    '\t\tloadDefaultKBConfig();\n'
    '#else\n'
    '\tloadInputConfig(mKeyboardInputConfig);\n'
    '#endif\n'
)
if keyboard_anchor not in text:
    raise SystemExit("could not find keyboard configuration anchor")
text = text.replace(keyboard_anchor, keyboard_replacement, 1)

mouse_anchor = '\tcase SDL_KEYDOWN:\n'
mouse_cases = r'''
#ifdef WEBOS
	case SDL_MOUSEBUTTONDOWN:
	case SDL_MOUSEBUTTONUP:
		if(ev.button.button == SDL_BUTTON_LEFT || ev.button.button == SDL_BUTTON_RIGHT)
		{
			const int key = ev.button.button == SDL_BUTTON_LEFT ? SDLK_RETURN : SDLK_ESCAPE;
			window->input(getInputConfigByDevice(DEVICE_KEYBOARD),
				Input(DEVICE_KEYBOARD, TYPE_KEY, key, ev.button.state == SDL_PRESSED, false));
			return true;
		}
		return false;

	case SDL_MOUSEWHEEL:
		if(ev.wheel.y != 0)
		{
			const int key = ev.wheel.y > 0 ? SDLK_UP : SDLK_DOWN;
			window->input(getInputConfigByDevice(DEVICE_KEYBOARD), Input(DEVICE_KEYBOARD, TYPE_KEY, key, 1, false));
			window->input(getInputConfigByDevice(DEVICE_KEYBOARD), Input(DEVICE_KEYBOARD, TYPE_KEY, key, 0, false));
			return true;
		}
		return false;
#endif

'''
if mouse_anchor not in text:
    raise SystemExit("could not find SDL keyboard event anchor")
text = text.replace(mouse_anchor, mouse_cases + mouse_anchor, 1)

# webOS reserves its physical Back button before native SDL applications can
# reliably consume it. Translate buttons that do reach native apps into the
# standard RetroPie keyboard defaults. Numeric keys are present on many Magic
# Remotes; the official webOS color keycodes are useful on models exposing them.
keydown_anchor = (
    '\t\twindow->input(getInputConfigByDevice(DEVICE_KEYBOARD), '
    'Input(DEVICE_KEYBOARD, TYPE_KEY, ev.key.keysym.sym, 1, false));\n'
    '\t\treturn true;\n\n'
    '\tcase SDL_KEYUP:\n'
    '\t\twindow->input(getInputConfigByDevice(DEVICE_KEYBOARD), '
    'Input(DEVICE_KEYBOARD, TYPE_KEY, ev.key.keysym.sym, 0, false));\n'
    '\t\treturn true;\n'
)
keydown_replacement = r'''		int mappedKey = ev.key.keysym.sym;
#ifdef WEBOS
		// 0 / red / Back -> B (Escape)
		if(mappedKey == SDLK_0 || mappedKey == 403 || mappedKey == 461)
			mappedKey = SDLK_ESCAPE;
		// 1 / green -> Start (F1), opens the EmulationStation menu
		else if(mappedKey == SDLK_1 || mappedKey == 404)
			mappedKey = SDLK_F1;
		// 2 / yellow -> Select (F2)
		else if(mappedKey == SDLK_2 || mappedKey == 405)
			mappedKey = SDLK_F2;
#endif
		window->input(getInputConfigByDevice(DEVICE_KEYBOARD), Input(DEVICE_KEYBOARD, TYPE_KEY, mappedKey, 1, false));
		return true;

	case SDL_KEYUP:
	{
		int mappedKey = ev.key.keysym.sym;
#ifdef WEBOS
		if(mappedKey == SDLK_0 || mappedKey == 403 || mappedKey == 461)
			mappedKey = SDLK_ESCAPE;
		else if(mappedKey == SDLK_1 || mappedKey == 404)
			mappedKey = SDLK_F1;
		else if(mappedKey == SDLK_2 || mappedKey == 405)
			mappedKey = SDLK_F2;
#endif
		window->input(getInputConfigByDevice(DEVICE_KEYBOARD), Input(DEVICE_KEYBOARD, TYPE_KEY, mappedKey, 0, false));
		return true;
	}
'''
if keydown_anchor not in text:
    raise SystemExit("could not find keyboard forwarding anchor")
text = text.replace(keydown_anchor, keydown_replacement, 1)
input_manager.write_text(text)

# RetroPie normally enters the controller detection wizard unless an input file
# already exists on disk. The webOS in-memory fallback above is intentionally a
# valid first-run configuration, so allow it to proceed directly to the UI.
text = main_cpp.read_text()
input_check = (
    '\t\tif(Utils::FileSystem::exists(InputManager::getConfigPath()) && '
    'InputManager::getInstance()->getNumConfiguredDevices() > 0)\n'
)
input_check_replacement = (
    '#ifdef WEBOS\n'
    '\t\tif(InputManager::getInstance()->getNumConfiguredDevices() > 0)\n'
    '#else\n'
    + input_check +
    '#endif\n'
)
if input_check not in text:
    raise SystemExit("could not find first-run input configuration check")
text = text.replace(input_check, input_check_replacement, 1)
main_cpp.write_text(text)

# RetroPie normally makes libVLC mandatory for video previews. A TV launcher
# does not need to drag an entire media stack into the IPK just to render the
# frontend. Keep the same class ABI but degrade video widgets to their static
# screenshot/thumbnail fallback on webOS.
vlc_cpp.write_text(r'''#include "components/VideoVlcComponent.h"

#include "resources/TextureResource.h"

libvlc_instance_t* VideoVlcComponent::mVLC = nullptr;
std::thread VideoVlcComponent::sCleanupThread;
std::mutex VideoVlcComponent::sCleanupMutex;
std::condition_variable VideoVlcComponent::sCleanupCond;
std::deque<std::function<void()>> VideoVlcComponent::sCleanupQueue;
bool VideoVlcComponent::sCleanupRunning = false;
bool VideoVlcComponent::sCleanupExit = false;

void VideoVlcComponent::setupVLC(std::string) {}
void VideoVlcComponent::deinit() {}
void VideoVlcComponent::cleanupWorker() {}
void VideoVlcComponent::postCleanupTask(std::function<void()>) {}

VideoVlcComponent::VideoVlcComponent(Window* window, std::string) :
    VideoComponent(window),
    mMedia(nullptr),
    mMediaPlayer(nullptr),
    mContext(nullptr),
    mTexture(TextureResource::get("")),
    mMediaParsing(false)
{
}

VideoVlcComponent::~VideoVlcComponent()
{
    stopVideo();
}

void VideoVlcComponent::render(const Transform4x4f& parentTrans)
{
    if (!isVisible())
        return;

    VideoComponent::render(parentTrans);
    VideoComponent::renderSnapshot(parentTrans);
}

void VideoVlcComponent::setResize(float width, float height)
{
    setSize(width, height);
    mTargetSize = Vector2f(width, height);
    mTargetIsMax = false;
    mStaticImage.setResize(width, height);
    onSizeChanged();
}

void VideoVlcComponent::setMaxSize(float width, float height)
{
    setSize(width, height);
    mTargetSize = Vector2f(width, height);
    mTargetIsMax = true;
    mStaticImage.setMaxSize(width, height);
    onSizeChanged();
}

void VideoVlcComponent::resize() {}

void VideoVlcComponent::startVideo()
{
    mIsPlaying = false;
    mPlayingVideoPath.clear();
}

void VideoVlcComponent::stopVideo()
{
    mIsPlaying = false;
    mStartDelayed = false;
    mPlayingVideoPath.clear();
}

void VideoVlcComponent::handleLooping() {}
void VideoVlcComponent::setMuteMode() {}
void VideoVlcComponent::setupContext() {}
void VideoVlcComponent::freeContext() {}
void VideoVlcComponent::handleParsing() {}
void VideoVlcComponent::onMediaParsed() {}
''')

print("Applied RetroPie EmulationStation webOS patches")
