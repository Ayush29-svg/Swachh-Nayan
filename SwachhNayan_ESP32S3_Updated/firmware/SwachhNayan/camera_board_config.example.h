#pragma once
// Copy to camera_board_config.h only after confirming the exact carrier schematic.
// Define every pin from that schematic. This is deliberately not a ready pinout.
#define CAMERA_BOARD_CONFIG { \\
  .pin_pwdn = CAMERA_PWDN_GPIO, .pin_reset = CAMERA_RESET_GPIO, \\
  .pin_xclk = CAMERA_XCLK_GPIO, .pin_sccb_sda = CAMERA_SIOD_GPIO, \\
  .pin_sccb_scl = CAMERA_SIOC_GPIO, .pin_d0 = CAMERA_D0_GPIO, \\
  .pin_d1 = CAMERA_D1_GPIO, .pin_d2 = CAMERA_D2_GPIO, .pin_d3 = CAMERA_D3_GPIO, \\
  .pin_d4 = CAMERA_D4_GPIO, .pin_d5 = CAMERA_D5_GPIO, .pin_d6 = CAMERA_D6_GPIO, \\
  .pin_d7 = CAMERA_D7_GPIO, .pin_vsync = CAMERA_VSYNC_GPIO, \\
  .pin_href = CAMERA_HREF_GPIO, .pin_pclk = CAMERA_PCLK_GPIO, \\
  .xclk_freq_hz = 20000000, .ledc_timer = LEDC_TIMER_0, .ledc_channel = LEDC_CHANNEL_0 \\
}
