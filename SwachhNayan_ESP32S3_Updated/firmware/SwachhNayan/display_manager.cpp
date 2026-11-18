#include "display_manager.h"
#include "config.h"

#if !MOCK_MODE
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

static LiquidCrystal_I2C* activeLcd = nullptr;
static uint8_t detectedAddr = 0;
static int activeSda = -1;
static int activeScl = -1;

static bool probeI2C(int sda, int scl, uint8_t& outAddr) {
    Wire.end();
    delay(10);
    Wire.begin(sda, scl, 100000);
    delay(10);

    // Check primary addresses first
    const uint8_t quickList[] = {0x27, 0x3F, 0x20, 0x38};
    for (uint8_t a : quickList) {
        Wire.beginTransmission(a);
        if (Wire.endTransmission() == 0) {
            outAddr = a;
            return true;
        }
    }
    // Full scan
    for (uint8_t a = 8; a < 120; a++) {
        Wire.beginTransmission(a);
        if (Wire.endTransmission() == 0) {
            outAddr = a;
            return true;
        }
    }
    return false;
}
#endif

bool DisplayManager::begin() {
#if MOCK_MODE
    ready = false;
#else
    // Candidate pin pairs to test: Priority to confirmed hardware pins (8, 9)
    struct PinPair { int sda; int scl; };
    const PinPair pairs[] = {
        {8, 9},                             // Confirmed hardware silkscreen SDA/SCL
        {Config::PIN_SDA, Config::PIN_SCL}, // (1, 2)
        {Config::PIN_SCL, Config::PIN_SDA}, // (2, 1) - Swapped
        {9, 8},
        {47, 48},
        {48, 47}
    };

    detectedAddr = 0;
    for (const auto& p : pairs) {
        Wire.end();
        delay(10);
        Wire.begin(p.sda, p.scl, 100000);
        delay(10);

        uint8_t err27 = 255, err3F = 255;
        Wire.beginTransmission(0x27);
        err27 = Wire.endTransmission();
        Wire.beginTransmission(0x3F);
        err3F = Wire.endTransmission();

        Serial.printf("[I2C_PROBE] Pins SDA=%d, SCL=%d -> 0x27 ret=%d, 0x3F ret=%d\n", p.sda, p.scl, err27, err3F);

        if (err27 == 0) {
            detectedAddr = 0x27;
            activeSda = p.sda; activeScl = p.scl;
            break;
        }
        if (err3F == 0) {
            detectedAddr = 0x3F;
            activeSda = p.sda; activeScl = p.scl;
            break;
        }
    }

    Serial.printf("[LCD_SUMMARY] Selected: SDA=%d, SCL=%d, ADDR=0x%02X\n", activeSda, activeScl, detectedAddr);

    if (detectedAddr == 0) {
        // Fall back to configured pins
        activeSda = Config::PIN_SDA;
        activeScl = Config::PIN_SCL;
        detectedAddr = Config::LCD_ADDRESS;
        Wire.end();
        Wire.begin(activeSda, activeScl, 100000);
        Serial.println("[LCD] No I2C response on any candidate pin. Using fallback (1, 2) @ 0x27.");
    }

    if (activeLcd) {
        delete activeLcd;
        activeLcd = nullptr;
    }
    activeLcd = new LiquidCrystal_I2C(detectedAddr, 16, 2);

    // Initialise LCD with Backlight strictly ON
    activeLcd->init();
    activeLcd->backlight();

    activeLcd->clear();
    activeLcd->setCursor(0, 0);
    activeLcd->print("SWACHH-NAYAN S3");
    activeLcd->setCursor(0, 1);
    char buf[17];
    snprintf(buf, 17, "SDA:%d SCL:%d 0x%X", activeSda, activeScl, detectedAddr);
    activeLcd->print(buf);
    ready = true;
#endif
    return ready;
}

void DisplayManager::reclaimBus() {
#if !MOCK_MODE
    if (!activeLcd) return;
    Wire.begin(activeSda, activeScl, 100000);
    activeLcd->backlight();
#endif
}

void DisplayManager::update(uint32_t now, const DistanceReading& d, const WaterReading& w,
                            const CameraStatus& c, const Prediction& p, SystemState s, bool servo) {
    if (now - last < 400) return; // Responsive 400ms display refresh
    last = now;

#if !MOCK_MODE
    if (!activeLcd) return;

    char line1[17] = {0};
    char line2[17] = {0};

    // PRIORITY 1: Active Waste / Package Detection Alert
    if (s == SystemState::WASTE_DETECTED || (p.valid && p.confidence >= Config::MIN_AI_CONFIDENCE)) {
        snprintf(line1, 17, "!PACKAGE DETECT!");
        if (p.valid) {
            snprintf(line2, 17, "%-10.10s %2.0f%%", p.label, p.confidence * 100.0f);
        } else {
            snprintf(line2, 17, "Dist: %4.1f cm", d.cm);
        }
    }
    // PRIORITY 2: Flap Actuating / Diverting
    else if (s == SystemState::DIVERTING || s == SystemState::DIVERSION_REQUESTED || servo) {
        snprintf(line1, 17, "* DIVERTING FLAP *");
        snprintf(line2, 17, "SWEEPING DEBRIS ");
    }
    // PRIORITY 3: Close Obstruction Warning
    else if (s == SystemState::POSSIBLE_OBSTRUCTION || (d.valid && d.cm < Config::OBSTRUCTION_DISTANCE_CM)) {
        snprintf(line1, 17, "OBSTRUCTION NEAR");
        snprintf(line2, 17, "D:%2.0fcm P:%s", d.valid ? d.cm : 0.0f, w.wet ? "WET" : "DRY");
    }
    // PRIORITY 4: Normal Monitoring Display
    else {
        page = (page + 1) % 2;
        if (page == 0) {
            snprintf(line1, 17, "SWACHH-NAYAN S3 ");
            snprintf(line2, 17, "D:%2.0fcm P:%s", d.valid ? d.cm : 0.0f, w.wet ? "WET" : "DRY");
        } else {
            snprintf(line1, 17, "DRAIN: CLEAR    ");
            snprintf(line2, 17, "Cam:%s AI:OK ", c.ready ? "RDY" : "OFF");
        }
    }

    activeLcd->setCursor(0, 0);
    activeLcd->print(line1);
    activeLcd->setCursor(0, 1);
    activeLcd->print(line2);
#endif
}
