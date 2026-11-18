#pragma once
#include <Arduino.h>

// Set MOCK_MODE to 0 to build the physical sensor, camera, SD, and LCD drivers.
#ifndef MOCK_MODE
#define MOCK_MODE 0
#endif
#ifndef CAMERA_ENABLED
#define CAMERA_ENABLED 1
#endif
#ifndef SD_CARD_ENABLED
#define SD_CARD_ENABLED 1
#endif
#ifndef SERVO_ENABLED
#define SERVO_ENABLED 1
#endif
#ifndef AI_MODEL_ENABLED
#define AI_MODEL_ENABLED 0
#endif
#ifndef WEB_DASHBOARD_ENABLED
#define WEB_DASHBOARD_ENABLED 1
#endif

namespace Config
{
    constexpr char WIFI_SSID[] = "Airtel_AP Wifi"; // Set your Wi-Fi network name.
    constexpr char WIFI_PASSWORD[] = "Sdr@3232";   // Set your Wi-Fi password.
    constexpr uint32_t SERIAL_BAUD = 115200;

    // CONFLICT-FREE PIN MAP FOR DUAL TYPE-C ESP32-S3-CAM (N16R8):
    // Internal Camera uses: 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17, 18
    // Internal MicroSD uses: 38 (CMD), 39 (CLK), 40 (D0)
    // External peripherals mapped to clean, conflict-free header pins:
    constexpr uint8_t PIN_TRIG = 41; // HC-SR04 Trig
    constexpr uint8_t PIN_ECHO = 42; // HC-SR04 Echo (resistor divider 5V->3.3V)
    constexpr uint8_t PIN_SDA  = 1;  // ADS1115 & LCD 16x2 SDA
    constexpr uint8_t PIN_SCL  = 2;  // ADS1115 & LCD 16x2 SCL
    constexpr uint8_t PIN_SERVO = 21; // Pin 21 is broken out and conflict-free for Servo PWM

    // MicroSD Card pins (SD_MMC 1-bit)
    constexpr int PIN_SD_CLK = 39;
    constexpr int PIN_SD_CMD = 38;
    constexpr int PIN_SD_D0  = 40;

    constexpr uint8_t ADS_ADDRESS = 0x48, ADS_CHANNEL = 0;
    constexpr uint8_t LCD_ADDRESS = 0x27, LCD_COLUMNS = 16, LCD_ROWS = 2;
    constexpr uint32_t DISTANCE_PERIOD_MS = 150, WATER_PERIOD_MS = 250;
    constexpr uint32_t CAMERA_PERIOD_MS = 3000, DISPLAY_PERIOD_MS = 1500;
    constexpr uint32_t DIAGNOSTIC_PERIOD_MS = 2000;
    constexpr uint32_t TELEMETRY_LOG_PERIOD_MS = 5000;
    constexpr uint32_t WIFI_CONNECT_TIMEOUT_MS = 15000;
    constexpr uint32_t ECHO_TIMEOUT_US = 25000;
    constexpr uint8_t DISTANCE_MEDIAN_N = 5, CONFIRM_COUNT = 2;
    constexpr float DISTANCE_MIN_CM = 4.0f, DISTANCE_MAX_CM = 400.0f;
    constexpr float OBSTRUCTION_DISTANCE_CM = 35.0f, MIN_AI_CONFIDENCE = 0.75f;

    // Calibration endpoints for HW-038 water sensor
    // In air (DRY): raw ~ 4000-4095. In water (WET): raw drops below 2500.
    constexpr int16_t WATER_DRY_RAW = 4000, WATER_WET_RAW = 1200;
    constexpr int16_t WATER_HYSTERESIS_RAW = 250;
    constexpr uint8_t PIN_WATER_ANALOG = 3; // Fallback analog pin if ADS1115 not used

    // Servo actuator settings (Configured for friend's original 90° center / 45° fire diversion)
    constexpr uint32_t SERVO_COOLDOWN_MS = 2500, SERVO_MOVE_TIMEOUT_MS = 2000;
    constexpr int SERVO_SAFE_DEG = 90, SERVO_DIVERT_DEG = 45;
    constexpr int SERVO_MIN_DEG = 0, SERVO_MAX_DEG = 180;
#ifndef SERVO_PIN
#define SERVO_PIN 21 // Pin 21 is broken out and conflict-free for Servo PWM
#endif
    constexpr bool ACTUATOR_ENABLED = (SERVO_ENABLED != 0) && (SERVO_PIN >= 0);
    constexpr bool ACTUATOR_TEST_ONLY = false;
    constexpr bool ACTUATOR_REQUIRE_WATER_WET = false;
}
