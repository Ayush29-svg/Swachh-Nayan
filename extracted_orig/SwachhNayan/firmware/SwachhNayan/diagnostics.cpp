#include "diagnostics.h"
#include "esp_heap_caps.h"
void Diagnostics::begin(){log("INFO","diagnostics online");}
void Diagnostics::log(const char*l,const char*m){Serial.printf("[%lu][%s] %s\n",(unsigned long)millis(),l,m);}
void Diagnostics::heartbeat(uint32_t now){static uint32_t last=0;if(now-last<10000)return;last=now;Serial.printf("[DIAG] uptime_ms=%lu heap=%u psram=%u\n",(unsigned long)now,(unsigned)ESP.getFreeHeap(),(unsigned)heap_caps_get_free_size(MALLOC_CAP_SPIRAM));}
uint32_t Diagnostics::freeHeap()const{return ESP.getFreeHeap();}
