#include "camera_manager.h"
#include "config.h"

#if CAMERA_ENABLED
#include "camera_board_config.h"
#include "esp_camera.h"
#include "esp_rom_gpio.h"
#include "soc/gpio_sig_map.h"
#include <Wire.h>
#endif

void CameraManager::prepareCamBus() {
#if CAMERA_ENABLED
    Wire.end();
    pinMode(8, INPUT);
    pinMode(9, INPUT);
    esp_rom_gpio_connect_in_signal(8, CAM_DATA_IN2_IDX, false);
    esp_rom_gpio_connect_in_signal(9, CAM_DATA_IN1_IDX, false);

    sensor_t *s = esp_camera_sensor_get();
    if (s && s->set_reg) {
        s->set_reg(s, 0x3018, 0xFF, 0xFF);
        s->set_reg(s, 0x3017, 0xFF, 0xFF);
    }
#endif
}

void CameraManager::reclaimI2CBus() {
#if CAMERA_ENABLED
    sensor_t *s = esp_camera_sensor_get();
    if (s && s->set_reg) {
        s->set_reg(s, 0x3018, 0xFF, 0x00);
        s->set_reg(s, 0x3017, 0xFF, 0x00);
    }
#endif
}

bool CameraManager::begin() {
#if CAMERA_ENABLED
    camera_config_t c = getCameraBoardConfig();
    c.frame_size = FRAMESIZE_QVGA;       // 320x240
    c.pixel_format = PIXFORMAT_JPEG;     // Direct hardware JPEG
    c.jpeg_quality = 12;                 // Balanced size and clarity
    c.fb_count = 2;                      // Double buffer in PSRAM
    c.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
    c.fb_location = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
    c.xclk_freq_hz = 20000000;          // 20MHz standard clock

    esp_err_t e = esp_camera_init(&c);
    Serial.printf("[CAM_INIT] Init result: 0x%X\n", (unsigned)e);
    if (e != ESP_OK) {
        c.xclk_freq_hz = 10000000;
        e = esp_camera_init(&c);
        Serial.printf("[CAM_INIT] Fallback 10MHz result: 0x%X\n", (unsigned)e);
    }

    status.ready = (e == ESP_OK);
    if (status.ready) {
        sensor_t *s = esp_camera_sensor_get();
        if (s) {
            Serial.printf("[CAM_INIT] Sensor detected, PID: 0x%04X\n", s->id.PID);
            s->set_vflip(s, 1);
            s->set_hmirror(s, 0);
        }
        status.error = "OK";
        reclaimI2CBus();
    } else {
        status.error = "CAMERA_INIT_FAILED";
    }
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

    prepareCamBus();
    delay(5);

    camera_fb_t *fb = esp_camera_fb_get();
    reclaimI2CBus();

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
