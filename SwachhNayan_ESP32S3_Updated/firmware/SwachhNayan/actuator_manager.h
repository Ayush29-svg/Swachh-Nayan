#pragma once
#include <Arduino.h>

class ActuatorManager {
public:
    bool begin();
    void requestMove(bool divert, uint32_t now);
    void moveTo(int angle, uint32_t now);
    void trigger2xSweep(uint32_t now);
    void update(uint32_t now);
    bool active() const { return moving || sweeping; }
    bool isSweeping() const { return sweeping; }
    int currentAngle() const { return curAngle; }

private:
    bool ready = false;
    bool moving = false;
    bool sweeping = false;
    uint8_t sweepStep = 0;
    uint32_t stepStart = 0;
    uint32_t started = 0;
    uint32_t lastAction = 0;
    int target = 0;
    int curAngle = 0;
};

