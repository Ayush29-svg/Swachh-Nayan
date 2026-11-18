#include "actuator_manager.h"
#include "config.h"
#include <esp_camera.h>
#include "driver/gpio.h"

// Synchronized servo candidate pins: GPIO 21 (primary header), GPIO 48, GPIO 47, GPIO 14
static const uint8_t SERVO_PINS[] = { 21, 48, 47, 14 };
static const uint8_t NUM_PINS = sizeof(SERVO_PINS) / sizeof(SERVO_PINS[0]);

// Standard 50Hz RC servo PWM via ESP32 Hardware LEDC (12-bit resolution):
// 50Hz period = 20,000 microseconds (20ms).
// 12-bit resolution: 4096 counts per 20,000 us (~4.88 us/count).
// 0 deg   = 500 us  -> duty = (500  * 4096) / 20000 = 102
// 45 deg  = 1000 us -> duty = (1000 * 4096) / 20000 = 204 (Full Left)
// 90 deg  = 1500 us -> duty = (1500 * 4096) / 20000 = 307 (Neutral Center)
// 135 deg = 2000 us -> duty = (2000 * 4096) / 20000 = 409 (Full Right)
// 180 deg = 2500 us -> duty = (2500 * 4096) / 20000 = 512
static inline uint32_t angleToDuty(int angle) {
    if (angle < 0) angle = 0;
    if (angle > 180) angle = 180;
    uint32_t pulse_us = 500 + ((uint32_t)angle * 2000UL) / 180UL;
    return (pulse_us * 4096UL) / 20000UL;
}

static void applyAngleToHardware(int angle) {
    uint32_t duty = angleToDuty(angle);
    for (uint8_t i = 0; i < NUM_PINS; i++) {
        ledcWrite(SERVO_PINS[i], duty);
    }
}

bool ActuatorManager::begin() {
    ready = true;
    moving = false;
    sweeping = false;
    curAngle = Config::SERVO_SAFE_DEG;
    target = Config::SERVO_SAFE_DEG;

    // Attach hardware LEDC 50Hz 12-bit PWM across all candidate pins
    for (uint8_t i = 0; i < NUM_PINS; i++) {
        bool ok = ledcAttach(SERVO_PINS[i], 50, 12);
        gpio_set_drive_capability((gpio_num_t)SERVO_PINS[i], GPIO_DRIVE_CAP_3);
        Serial.printf("[SERVO_INIT] Pin %d (LEDC 50Hz 12-bit) -> %s\n", SERVO_PINS[i], ok ? "ATTACHED" : "FAILED");
    }

    applyAngleToHardware(Config::SERVO_SAFE_DEG);
    return true;
}

void ActuatorManager::moveTo(int angle, uint32_t now) {
    if (!ready) begin();
    if (angle < Config::SERVO_MIN_DEG) angle = Config::SERVO_MIN_DEG;
    if (angle > Config::SERVO_MAX_DEG) angle = Config::SERVO_MAX_DEG;
    target = angle;
    curAngle = target;
    applyAngleToHardware(target);
    uint32_t duty = angleToDuty(target);
    Serial.printf("[SERVO_MOVE] Target=%d deg (Duty=%u/4096)\n", target, (unsigned)duty);

    started = now;
    lastAction = now;
    moving = (target != Config::SERVO_SAFE_DEG);
}

void ActuatorManager::requestMove(bool divert, uint32_t now) {
    if (!ready) begin();
    if (divert) {
        trigger2xSweep(now);
    } else {
        moveTo(Config::SERVO_SAFE_DEG, now);
    }
}

static const int SWEEP_ANGLES[] = { 45, 135, 45, 135, 90 };
static const uint32_t STEP_DURATIONS_MS[] = { 600, 650, 600, 650, 400 };
static const uint8_t TOTAL_SWEEP_STEPS = 5;

void ActuatorManager::trigger2xSweep(uint32_t now) {
    if (!ready) begin();
    if (sweeping) return; // already sweeping, ignore until 2-cycle finishes

    sweeping = true;
    sweepStep = 0;
    stepStart = now;
    moveTo(SWEEP_ANGLES[0], now);
    Serial.println("[SWEEP] >>> 2-Cycle 90° Sweep STARTED (Cycle 1 Left: 45°)");
}

void ActuatorManager::update(uint32_t now) {
    if (sweeping) {
        if (now - stepStart >= STEP_DURATIONS_MS[sweepStep]) {
            sweepStep++;
            if (sweepStep < TOTAL_SWEEP_STEPS) {
                stepStart = now;
                moveTo(SWEEP_ANGLES[sweepStep], now);
                if (sweepStep == 1) Serial.println("[SWEEP] >>> Cycle 1: Sweep RIGHT (135°)");
                else if (sweepStep == 2) Serial.println("[SWEEP] >>> Cycle 2: Sweep LEFT (45°)");
                else if (sweepStep == 3) Serial.println("[SWEEP] >>> Cycle 2: Sweep RIGHT (135°)");
                else if (sweepStep == 4) Serial.println("[SWEEP] >>> Park: Return to CENTER (90°)");
            } else {
                sweeping = false;
                moving = false;
                moveTo(Config::SERVO_SAFE_DEG, now);
                Serial.println("[SWEEP] >>> 2-Cycle 90° Sweep COMPLETE. Armed for new object.");
            }
        }
        return;
    }

    if (!moving) return;
    if (now - started >= Config::SERVO_MOVE_TIMEOUT_MS) {
        moveTo(Config::SERVO_SAFE_DEG, now);
        moving = false;
    }
}
