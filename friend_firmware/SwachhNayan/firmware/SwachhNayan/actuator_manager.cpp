#include "actuator_manager.h"
#include "config.h"
#if SERVO_ENABLED
#include <ESP32Servo.h>
static Servo servo;
#endif
bool ActuatorManager::begin(){
#if SERVO_ENABLED
 if(Config::SERVO_MIN_DEG>=Config::SERVO_MAX_DEG||Config::SERVO_SAFE_DEG<Config::SERVO_MIN_DEG||Config::SERVO_SAFE_DEG>Config::SERVO_MAX_DEG)return false;
 // No attach or movement at boot; hardware will remain uncommanded until an explicit request.
 ready=true;
#else
 ready=false;
#endif
 return ready;}
void ActuatorManager::requestMove(bool divert,uint32_t now){if(!ready||moving||now-lastAction<Config::SERVO_COOLDOWN_MS)return;target=divert?Config::SERVO_DIVERT_DEG:Config::SERVO_SAFE_DEG;if(target<Config::SERVO_MIN_DEG||target>Config::SERVO_MAX_DEG)return;
#if SERVO_ENABLED
 if(SERVO_PIN<0)return;if(!servo.attached()){servo.setPeriodHertz(50);servo.attach(SERVO_PIN,500,2500);}servo.write(target);
#endif
 started=now;lastAction=now;moving=true;}
void ActuatorManager::update(uint32_t now){if(!moving)return;if(now-started>=Config::SERVO_MOVE_TIMEOUT_MS){
#if SERVO_ENABLED
 servo.write(Config::SERVO_SAFE_DEG);
#endif
 moving=false;}}
