#include "display_manager.h"
#include "config.h"

#if !MOCK_MODE
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
static LiquidCrystal_I2C lcd(Config::LCD_ADDRESS, Config::LCD_COLUMNS, Config::LCD_ROWS);
#endif

bool DisplayManager::begin() {
#if MOCK_MODE
    ready = false;
#else
    lcd.init();
    lcd.backlight();
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("SWACHH-NAYAN S3");
    lcd.setCursor(0, 1);
    lcd.print("SYSTEM READY");
    ready = true;
#endif
    return ready;
}

void DisplayManager::update(uint32_t now, const DistanceReading& d, const WaterReading& w,
                            const CameraStatus& c, const Prediction& p, SystemState s, bool servo) {
    if (now - last < 500) return; // Responsive 500ms display refresh
    last = now;

#if !MOCK_MODE
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
        snprintf(line2, 17, "Dist: %5.1f cm  ", d.cm);
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

    lcd.setCursor(0, 0);
    lcd.print(line1);
    lcd.setCursor(0, 1);
    lcd.print(line2);
#endif
}
