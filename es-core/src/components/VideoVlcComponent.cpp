#include "components/VideoVlcComponent.h"

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
