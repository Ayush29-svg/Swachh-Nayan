#include "decision_engine.h"
#include "config.h"

void DecisionEngine::begin() {
    current = SystemState::MONITORING;
    nearCount = 0;
    objectLatched = false;
}

const char* DecisionEngine::name(SystemState s) {
    switch (s) {
        case SystemState::STARTUP: return "STARTUP";
        case SystemState::SELF_TEST: return "SELF_TEST";
        case SystemState::MONITORING: return "MONITORING";
        case SystemState::POSSIBLE_OBSTRUCTION: return "POSSIBLE_OBSTRUCTION";
        case SystemState::WASTE_DETECTED: return "WASTE_DETECTED";
        case SystemState::DIVERSION_REQUESTED: return "DIVERSION_REQUESTED";
        case SystemState::DIVERTING: return "DIVERTING";
        case SystemState::RECOVERY: return "RECOVERY";
        case SystemState::SENSOR_FAULT: return "SENSOR_FAULT";
        case SystemState::CAMERA_FAULT: return "CAMERA_FAULT";
        case SystemState::SAFE_MODE: return "SAFE_MODE";
    }
    return "UNKNOWN";
}

Decision DecisionEngine::update(const DistanceReading& d, const WaterReading& w,
                               bool cameraReady, bool cameraFault,
                               const Prediction& p, bool manual) {
    bool request = false;
    bool candidate = false;

    // Check camera fault
    if (cameraFault) {
        current = SystemState::CAMERA_FAULT;
        nearCount = 0;
        return {current, false, false};
    }

    // Ultrasonic object detection (ignoring < 4cm blind spot)
    bool near = d.valid && (d.cm >= Config::DISTANCE_MIN_CM) && (d.cm < Config::OBSTRUCTION_DISTANCE_CM);
    if (near) {
        nearCount = (nearCount < 255) ? (nearCount + 1) : 255;
    } else {
        if (nearCount > 0) nearCount--;
    }

    // AI Prediction check
    bool pred = cameraReady && p.valid && (p.confidence >= Config::MIN_AI_CONFIDENCE);
    candidate = pred;

    if (manual) {
        current = SystemState::DIVERSION_REQUESTED;
        request = Config::ACTUATOR_ENABLED;
    } else if (pred && nearCount >= Config::CONFIRM_COUNT) {
        current = SystemState::DIVERSION_REQUESTED;
        if (!objectLatched && Config::ACTUATOR_ENABLED) {
            request = true;
            objectLatched = true;
        }
    } else if (pred) {
        current = SystemState::WASTE_DETECTED;
    } else if (nearCount >= Config::CONFIRM_COUNT) {
        current = SystemState::POSSIBLE_OBSTRUCTION;
        if (!objectLatched && Config::ACTUATOR_ENABLED && !Config::ACTUATOR_TEST_ONLY) {
            request = true;
            objectLatched = true;
        }
    } else if (!d.valid && (d.timestamp > 0)) {
        current = SystemState::SENSOR_FAULT;
    } else {
        current = SystemState::MONITORING;
    }

    // Re-arm when object moves away / area is clear
    if (!near && !pred && nearCount == 0) {
        objectLatched = false;
    }

    return {current, request, candidate};
}
