#include "sensor_water.h"
#include "config.h"
#if !MOCK_MODE
#include <Wire.h>
#include <Adafruit_ADS1X15.h>
static Adafruit_ADS1115 ads;
#endif
bool WaterSensor::begin(){
  dry=Config::WATER_DRY_RAW; wetRef=Config::WATER_WET_RAW;
#if MOCK_MODE
  ready=true;
#else
  ready=ads.begin(Config::ADS_ADDRESS,&Wire);
#endif
  return ready;
}
void WaterSensor::update(uint32_t now){
  if(!ready||now-last<Config::WATER_PERIOD_MS)return;
  last=now;
#if MOCK_MODE
  int16_t r=1094;
#else
  int16_t r=ads.readADC_SingleEnded(Config::ADS_CHANNEL);
#endif
  value.raw=r;value.timestamp=now;value.valid=true;accum+=r;if(++n<4)return;
  int16_t avg=accum/n;accum=0;n=0;value.raw=avg;
  if(dry<0||wetRef<0||dry==wetRef){value.valid=true;return;}
  int32_t mid=(int32_t(dry)+wetRef)/2;int32_t h=Config::WATER_HYSTERESIS_RAW;
  if(!haveState){wet=(wetRef>dry)?avg>=mid:avg<=mid;haveState=true;}
  else if(wetRef>dry){if(avg>mid+h)wet=true;else if(avg<mid-h)wet=false;}
  else{if(avg<mid-h)wet=true;else if(avg>mid+h)wet=false;}
  value.wet=wet;
}
WaterReading WaterSensor::reading()const{return value;}
void WaterSensor::calibrateDry(){if(value.valid)dry=value.raw;}
void WaterSensor::calibrateWet(){if(value.valid)wetRef=value.raw;}
bool WaterSensor::calibrated()const{return dry>=0&&wetRef>=0&&dry!=wetRef;}
