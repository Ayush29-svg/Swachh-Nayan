#pragma once
#include <Arduino.h>
#include "sensor_ultrasonic.h"
#include "sensor_water.h"
#include "ai_inference.h"
enum class SystemState:uint8_t{STARTUP,SELF_TEST,MONITORING,POSSIBLE_OBSTRUCTION,WASTE_DETECTED,DIVERSION_REQUESTED,DIVERTING,RECOVERY,SENSOR_FAULT,CAMERA_FAULT,SAFE_MODE};
struct Decision {SystemState state;bool servoRequest;bool wasteCandidate;};
class DecisionEngine{public:void begin();Decision update(const DistanceReading&,const WaterReading&,bool cameraReady,bool cameraFault,const Prediction&,bool manual);SystemState state()const{return current;}static const char*name(SystemState);private:SystemState current=SystemState::STARTUP;uint8_t nearCount=0;bool objectLatched=false;};
