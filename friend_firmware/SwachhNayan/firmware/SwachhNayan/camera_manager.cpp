#include "camera_manager.h"
#include "config.h"

#if CAMERA_ENABLED
#include "camera_board_config.h"
#include "esp_camera.h"
#endif

bool CameraManager::begin() {
#if CAMERA_ENABLED
    camera_config_t c = getCameraBoardConfig();
    c.frame_size = FRAMESIZE_QVGA;       // 320x240
    c.pixel_format = PIXFORMAT_JPEG;     // Direct hardware JPEG
    c.jpeg_quality = 12;                 // Balanced size and clarity
    c.fb_count = 2;
    c.grab_mode = CAMERA_GRAB_LATEST;

    if (psramFound()) {
        c.fb_location = CAMERA_FB_IN_PSRAM;
    } else {
        status.error = "PSRAM_UNAVAILABLE";
        return false;
    }

    esp_err_t e = esp_camera_init(&c);
    status.ready = (e == ESP_OK);
    status.error = status.ready ? "OK" : "CAMERA_INIT_FAILED";
    return status.ready;
#else
    status.ready = false;
    status.error = "CAMERA_DISABLED_IN_CONFIG";
    return false;
#endif
}

CameraStatus CameraManager::capture(uint32_t now) {
    status.timestamp = now;
#if CAMERA_ENABLED
    if (!status.ready) {
        status.frameValid = false;
        status.error = "CAMERA_NOT_READY";
        return status;
    }
    if (frameHandle) {
        releaseFrame();
    }
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
        status.frameValid = false;
        status.error = "CAPTURE_FAILED";
        return status;
    }
    status.frameValid = fb->len > 0;
    status.frameBytes = fb->len;
    status.error = status.frameValid ? "OK" : "EMPTY_FRAME";
    frameHandle = fb;
    data = fb->buf;
#else
    (void)now;
    status.frameValid = false;
    status.error = "CAMERA_DISABLED_IN_CONFIG";
#endif
    return status;
}

const uint8_t* CameraManager::frameData() const {
    return data;
}

void CameraManager::releaseFrame() {
#if CAMERA_ENABLED
    if (frameHandle) {
        esp_camera_fb_return((camera_fb_t*)frameHandle);
    }
#endif
    frameHandle = nullptr;
    data = nullptr;
    status.frameValid = false;
    status.frameBytes = 0;
}

void CameraManager::end() {
    releaseFrame();
#if CAMERA_ENABLED
    esp_camera_deinit();
#endif
    status.ready = false;
}
