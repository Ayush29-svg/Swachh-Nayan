#pragma once
#include <Arduino.h>
#include "decision_engine.h"
#include "sensor_ultrasonic.h"
#include "sensor_water.h"
#include "camera_manager.h"
#include "ai_inference.h"
#include "sd_card_manager.h"

struct DashboardData {
    const char *mode = "DEVICE";
    SystemState state = SystemState::STARTUP;
    DistanceReading distance{0, false, 0};
    WaterReading water{0, false, false, 0};
    bool waterCalibrated = false;
    CameraStatus camera{false, false, 0, 0, "NOT_CONFIGURED"};
    Prediction prediction{};
    SDCardStatus sdCard{false, 0, 0, 0, "NOT_INITIALIZED"};
    bool servoActive = false;
    bool actuatorEnabled = false;
    int wifiRssi = 0;
    uint32_t freeHeap = 0;
    uint32_t uptimeMs = 0;
};

class WebDashboard {
public:
    bool begin();
    void update(const DashboardData &d);
    void loop();
    bool online() const { return isOnline; }
private:
    bool isOnline = false;
    bool wifiStarted = false;
    DashboardData current;
};
