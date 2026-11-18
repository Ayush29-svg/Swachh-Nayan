#include "sensor_water.h"
#include "config.h"
#if !MOCK_MODE
#include <Wire.h>
#include <Adafruit_ADS1X15.h>
static Adafruit_ADS1115 ads;
#endif

bool WaterSensor::begin() {
  dry = Config::WATER_DRY_RAW;
  wetRef = Config::WATER_WET_RAW;
#if MOCK_MODE
  ready = true;
#else
  pinMode(Config::PIN_WATER_ANALOG, INPUT);
  ready = ads.begin(Config::ADS_ADDRESS, &Wire);
  if (!ready) {
    Serial.printf("[WATER] ADS1115 not responding at 0x%02X. Using onboard ADC pin GPIO %d (PIN_WATER_ANALOG).\n",
                  Config::ADS_ADDRESS, Config::PIN_WATER_ANALOG);
  } else {
    Serial.printf("[WATER] ADS1115 initialized successfully at 0x%02X.\n", Config::ADS_ADDRESS);
  }
#endif
  return true;
}

void WaterSensor::update(uint32_t now) {
  if (now - last < Config::WATER_PERIOD_MS) return;
  last = now;

#if MOCK_MODE
  int16_t r = 1094;
#else
  int16_t r = -1;
  if (ready) {
    int16_t ads_val = ads.readADC_SingleEnded(Config::ADS_CHANNEL);
    if (ads_val > 10 && ads_val < 32000) {
      r = ads_val;
    }
  }
  // Read clean dedicated onboard ADC pin (GPIO 3)
  if (r < 0) {
    r = (int16_t)analogRead(Config::PIN_WATER_ANALOG);
  }
#endif

  value.raw = r;
  value.timestamp = now;
  value.valid = true;
  accum += r;
  if (++n < 4) return;
  int16_t avg = accum / n;
  accum = 0;
  n = 0;
  value.raw = avg;

  if (dry >= 0 && wetRef >= 0 && dry != wetRef) {
    int32_t mid = (int32_t(dry) + wetRef) / 2;
    int32_t h = Config::WATER_HYSTERESIS_RAW;
    if (!haveState) {
      wet = (wetRef > dry) ? (avg >= mid) : (avg <= mid);
      haveState = true;
    } else if (wetRef > dry) {
      if (avg > mid + h) wet = true;
      else if (avg < mid - h) wet = false;
    } else {
      if (avg < mid - h) wet = true;
      else if (avg > mid + h) wet = false;
    }
  } else {
    // Dynamic fallback threshold based on sensor range
    int32_t threshold = (avg > 4095) ? 14000 : 2000;
    wet = (avg < threshold);
  }
  value.wet = wet;
}

WaterReading WaterSensor::reading() const { return value; }
void WaterSensor::calibrateDry() { if (value.valid) dry = value.raw; }
void WaterSensor::calibrateWet() { if (value.valid) wetRef = value.raw; }
bool WaterSensor::calibrated() const { return dry >= 0 && wetRef >= 0 && dry != wetRef; }
