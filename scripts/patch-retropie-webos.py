#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch-retropie-webos.py <RetroPie EmulationStation source>")

root = Path(sys.argv[1]).resolve()
cmake = root / "CMakeLists.txt"
volume_h = root / "es-app/src/VolumeControl.h"
volume_cpp = root / "es-app/src/VolumeControl.cpp"
vlc_cpp = root / "es-core/src/components/VideoVlcComponent.cpp"

for path in (cmake, volume_h, volume_cpp, vlc_cpp):
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
