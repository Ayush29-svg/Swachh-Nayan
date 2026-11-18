#pragma once
#include <Arduino.h>

struct SDCardStatus {
    bool mounted;
    uint32_t totalMB;
    uint32_t usedMB;
    uint32_t snapshotsSaved;
    const char *lastError;
};

class SDCardManager {
public:
    bool begin();
    bool isMounted() const { return status.mounted; }
    SDCardStatus getStatus() const { return status; }
    bool saveSnapshot(const uint8_t *jpegData, size_t len, const char *label);
    bool logTelemetry(uint32_t timestamp, float distanceCm, bool distanceValid, int16_t waterRaw, bool waterWet, bool waterValid, const char *state, const char *predictionLabel, float confidence);
private:
    SDCardStatus status{false, 0, 0, 0, "NOT_INITIALIZED"};
};
