#pragma once
#include "esp_camera.h"

// Hardware pin mapping for Generic Dual Type-C ESP32-S3-CAM (N16R8) with OV2640 / OV3660 / OV5640
#define CAMERA_PWDN_GPIO   -1
#define CAMERA_RESET_GPIO  -1
#define CAMERA_XCLK_GPIO   15
#define CAMERA_SIOD_GPIO    4
#define CAMERA_SIOC_GPIO    5

#define CAMERA_D7_GPIO      9  // Y9
#define CAMERA_D6_GPIO     16  // Y8
#define CAMERA_D5_GPIO     18  // Y7
#define CAMERA_D4_GPIO     17  // Y6
#define CAMERA_D3_GPIO      8  // Y5
#define CAMERA_D2_GPIO     11  // Y4
#define CAMERA_D1_GPIO     12  // Y3
#define CAMERA_D0_GPIO     10  // Y2

#define CAMERA_VSYNC_GPIO   6
#define CAMERA_HREF_GPIO    7
#define CAMERA_PCLK_GPIO   13

inline camera_config_t getCameraBoardConfig() {
    camera_config_t c{};
    c.pin_pwdn = CAMERA_PWDN_GPIO;
    c.pin_reset = CAMERA_RESET_GPIO;
    c.pin_xclk = CAMERA_XCLK_GPIO;
    c.pin_sccb_sda = CAMERA_SIOD_GPIO;
    c.pin_sccb_scl = CAMERA_SIOC_GPIO;
    c.pin_d7 = CAMERA_D7_GPIO;
    c.pin_d6 = CAMERA_D6_GPIO;
    c.pin_d5 = CAMERA_D5_GPIO;
    c.pin_d4 = CAMERA_D4_GPIO;
    c.pin_d3 = CAMERA_D3_GPIO;
    c.pin_d2 = CAMERA_D2_GPIO;
    c.pin_d1 = CAMERA_D1_GPIO;
    c.pin_d0 = CAMERA_D0_GPIO;
    c.pin_vsync = CAMERA_VSYNC_GPIO;
    c.pin_href = CAMERA_HREF_GPIO;
    c.pin_pclk = CAMERA_PCLK_GPIO;
    c.xclk_freq_hz = 10000000; // 10MHz safe frequency for OV2640 & OV3660 stability
    c.ledc_timer = LEDC_TIMER_0;
    c.ledc_channel = LEDC_CHANNEL_0;
    return c;
}
