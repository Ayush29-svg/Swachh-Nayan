#pragma once
#include <Arduino.h>
class Diagnostics{public:void begin();void log(const char*level,const char*message);void heartbeat(uint32_t now);uint32_t freeHeap()const;};
