#pragma once
#include <Arduino.h>
struct WaterReading { int16_t raw; bool valid; bool wet; uint32_t timestamp; };
class WaterSensor { public: bool begin(); void update(uint32_t now); WaterReading reading()const; void calibrateDry(); void calibrateWet(); bool calibrated()const;
 private: bool ready=false,wet=false,haveState=false; int16_t dry=-1,wetRef=-1; WaterReading value{0,false,false,0}; uint32_t last=0; int32_t accum=0; uint8_t n=0;
};
