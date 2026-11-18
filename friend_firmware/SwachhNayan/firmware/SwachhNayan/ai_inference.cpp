#include "ai_inference.h"
#include "config.h"
void AIInference::begin(){}
Prediction AIInference::infer(const uint8_t *,size_t){Prediction p{};strlcpy(p.label,"UNAVAILABLE",sizeof(p.label));p.valid=false;p.mock=false;p.inferenceMs=0;
#if AI_MODEL_ENABLED
  // Integrate the model runtime/preprocessing here; enable only after adding tested model artifacts.
  strlcpy(p.label,"NO_MODEL_ADAPTER",sizeof(p.label));
#endif
  return p;}
Prediction AIInference::mockPrediction(const char *label,float confidence){Prediction p{};strlcpy(p.label,label,sizeof(p.label));p.confidence=confidence;p.valid=confidence>=0&&confidence<=1;p.mock=true;p.inferenceMs=0;return p;}
