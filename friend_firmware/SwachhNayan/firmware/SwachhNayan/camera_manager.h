#pragma once
#include <Arduino.h>

struct CameraStatus {
    bool ready;
    bool frameValid;
    size_t frameBytes;
    uint32_t timestamp;
    const char *error;
};

class CameraManager {
    CameraStatus status{false, false, 0, 0, "NOT_INITIALIZED"};
    void *frameHandle = nullptr;
    const uint8_t *data = nullptr;
public:
    bool begin();
    CameraStatus capture(uint32_t now);
    const uint8_t* frameData() const;
    size_t frameBytes() const { return status.frameBytes; }
    void releaseFrame();
    void end();
    bool available() const { return status.ready; }
    CameraStatus lastStatus() const { return status; }
};
