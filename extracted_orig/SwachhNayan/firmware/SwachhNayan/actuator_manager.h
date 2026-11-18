#pragma once
#include <Arduino.h>
class ActuatorManager{public:bool begin();void requestMove(bool divert,uint32_t now);void update(uint32_t now);bool active()const{return moving;}private:bool ready=false,moving=false;uint32_t started=0,lastAction=0;int target=90;};
