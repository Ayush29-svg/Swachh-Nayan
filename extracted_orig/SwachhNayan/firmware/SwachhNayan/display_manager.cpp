#include "display_manager.h"
#include "config.h"
#if !MOCK_MODE
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
static LiquidCrystal_I2C lcd(Config::LCD_ADDRESS,Config::LCD_COLUMNS,Config::LCD_ROWS);
#endif
bool DisplayManager::begin(){
#if MOCK_MODE
 ready=false;
#else
 lcd.init();lcd.backlight();ready=true;
#endif
 return ready;}
void DisplayManager::update(uint32_t now,const DistanceReading&d,const WaterReading&w,const CameraStatus&c,const Prediction&p,SystemState s,bool servo){if(now-last<Config::DISPLAY_PERIOD_MS)return;last=now;page=(page+1)%4;
#if MOCK_MODE
 (void)d;(void)w;(void)c;(void)p;(void)s;(void)servo;
#else
 char a[17]={0},b[17]={0};switch(page){case 0:strncpy(a,"SWACHH-NAYAN",16);snprintf(b,17,"System: %.10s",DecisionEngine::name(s));break;case 1:if(d.valid)snprintf(a,17,"Dist: %5.1f cm",d.cm);else strncpy(a,"Dist: ERROR",16);if(!w.valid)strncpy(b,"Water: ERROR",16);else snprintf(b,17,"Water: %s",w.wet?"WET":"DRY/UNCAL");break;case 2:snprintf(a,17,"Camera: %s",c.ready?"READY":"UNAVAIL");snprintf(b,17,"AI: %.11s",p.valid?p.label:"UNKNOWN");break;default:snprintf(a,17,"Waste: %.10s",p.valid?p.label:"UNKNOWN");snprintf(b,17,"Servo: %s",servo?"ACTIVE":"SAFE");break;}lcd.clear();lcd.setCursor(0,0);lcd.print(a);lcd.setCursor(0,1);lcd.print(b);
#endif
}
