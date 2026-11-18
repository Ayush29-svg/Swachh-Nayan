#pragma once
#include <Arduino.h>
struct Prediction { char label[24]; float confidence; uint32_t inferenceMs; bool valid; bool mock; };
class AIInference { public: void begin(); Prediction infer(const uint8_t *rgb, size_t bytes); Prediction mockPrediction(const char *label,float confidence); };
