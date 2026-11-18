#pragma once
#include <Arduino.h>
#include "decision_engine.h"
#include "camera_manager.h"
class DisplayManager{public:bool begin();void update(uint32_t now,const DistanceReading&,const WaterReading&,const CameraStatus&,const Prediction&,SystemState,bool servoActive);private:uint8_t page=0;uint32_t last=0;bool ready=false;};
