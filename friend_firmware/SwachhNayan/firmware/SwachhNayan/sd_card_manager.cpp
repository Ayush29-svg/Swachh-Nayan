#include "sd_card_manager.h"
#include "config.h"

#if SD_CARD_ENABLED
#include <FS.h>
#include <SD_MMC.h>
#endif

bool SDCardManager::begin() {
#if SD_CARD_ENABLED
    // Dual Type-C ESP32-S3-CAM onboard TF socket: 1-bit SDMMC (CLK: 39, CMD: 38, D0: 40)
    SD_MMC.setPins(Config::PIN_SD_CLK, Config::PIN_SD_CMD, Config::PIN_SD_D0);
    if (!SD_MMC.begin("/sdcard", true)) { // 1-bit mode
        status.mounted = false;
        status.lastError = "MOUNT_FAILED";
        Serial.println("[SD] Mount failed. Card missing or not formatted as FAT32.");
        return false;
    }
    uint8_t cardType = SD_MMC.cardType();
    if (cardType == CARD_NONE) {
        status.mounted = false;
        status.lastError = "NO_CARD";
        Serial.println("[SD] No SD card detected in slot.");
        return false;
    }
    status.mounted = true;
    status.totalMB = (uint32_t)(SD_MMC.totalBytes() / (1024 * 1024));
    status.usedMB = (uint32_t)(SD_MMC.usedBytes() / (1024 * 1024));
    status.lastError = "OK";
    Serial.printf("[SD] Mounted: %u MB total, %u MB used.\n", status.totalMB, status.usedMB);

    if (!SD_MMC.exists("/captures")) {
        SD_MMC.mkdir("/captures");
    }

    if (!SD_MMC.exists("/telemetry.csv")) {
        File f = SD_MMC.open("/telemetry.csv", FILE_WRITE);
        if (f) {
            f.println("timestamp_ms,state,distance_cm,dist_valid,water_raw,water_wet,water_valid,prediction,confidence");
            f.close();
        }
    }
    return true;
#else
    status.mounted = false;
    status.lastError = "SD_DISABLED_IN_CONFIG";
    return false;
#endif
}

bool SDCardManager::saveSnapshot(const uint8_t *jpegData, size_t len, const char *label) {
#if SD_CARD_ENABLED
    if (!status.mounted || !jpegData || len == 0) return false;
    char path[64];
    snprintf(path, sizeof(path), "/captures/%s_%lu.jpg", label ? label : "snap", (unsigned long)millis());
    File f = SD_MMC.open(path, FILE_WRITE);
    if (!f) {
        status.lastError = "FILE_OPEN_FAILED";
        return false;
    }
    size_t written = f.write(jpegData, len);
    f.close();
    if (written == len) {
        status.snapshotsSaved++;
        status.usedMB = (uint32_t)(SD_MMC.usedBytes() / (1024 * 1024));
        Serial.printf("[SD] Saved snapshot: %s (%u bytes)\n", path, (unsigned)len);
        return true;
    }
    status.lastError = "WRITE_INCOMPLETE";
    return false;
#else
    (void)jpegData; (void)len; (void)label;
    return false;
#endif
}

bool SDCardManager::logTelemetry(uint32_t timestamp, float distanceCm, bool distanceValid, int16_t waterRaw, bool waterWet, bool waterValid, const char *state, const char *predictionLabel, float confidence) {
#if SD_CARD_ENABLED
    if (!status.mounted) return false;
    File f = SD_MMC.open("/telemetry.csv", FILE_APPEND);
    if (!f) return false;
    f.printf("%lu,%s,%.2f,%d,%d,%d,%d,%s,%.2f\n",
        (unsigned long)timestamp,
        state ? state : "UNKNOWN",
        distanceValid ? distanceCm : -1.0f,
        distanceValid ? 1 : 0,
        waterRaw,
        waterWet ? 1 : 0,
        waterValid ? 1 : 0,
        predictionLabel ? predictionLabel : "NONE",
        confidence
    );
    f.close();
    return true;
#else
    (void)timestamp; (void)distanceCm; (void)distanceValid; (void)waterRaw; (void)waterWet; (void)waterValid; (void)state; (void)predictionLabel; (void)confidence;
    return false;
#endif
}
