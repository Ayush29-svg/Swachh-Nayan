#pragma once
#include <Arduino.h>
struct DistanceReading { float cm; bool valid; uint32_t timestamp; };
class UltrasonicSensor {
 public: void begin(uint8_t trig, uint8_t echo); void update(uint32_t now); DistanceReading reading() const;
 private: uint8_t trigPin=0, echoPin=0, count=0, cursor=0; float samples[5]{}; DistanceReading current{0,false,0}; uint32_t last=0;
};
