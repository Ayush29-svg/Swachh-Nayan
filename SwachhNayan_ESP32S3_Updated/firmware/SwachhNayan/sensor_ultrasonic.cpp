#include "sensor_ultrasonic.h"
#include "config.h"

void UltrasonicSensor::begin(uint8_t trig, uint8_t echo) {
    trigPin = trig;
    echoPin = echo;
    pinMode(trigPin, OUTPUT);
    digitalWrite(trigPin, LOW);
    pinMode(echoPin, INPUT);
    current.cm = 25.0f;
    current.valid = false;
    current.timestamp = 0;
    count = 0;
    cursor = 0;
    glitchCount = 0;
}

void UltrasonicSensor::update(uint32_t now) {
    if (now - last < Config::DISTANCE_PERIOD_MS) return;
    last = now;

    // Send 10µs clean trigger pulse
    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);

    // Measure echo pulse width (timeout ~25ms / ~4m)
    uint32_t us = pulseIn(echoPin, HIGH, Config::ECHO_TIMEOUT_US);
    current.timestamp = now;

    if (!us) {
        // Echo timed out or missed reflection
        glitchCount++;
        // Keep last known valid reading for up to 3 missed cycles before invalidating
        if (glitchCount > 3) {
            current.valid = false;
        }
        return;
    }

    glitchCount = 0;
    float cm = (us * 0.0343f) / 2.0f;

    // Range sanity check
    if (cm < Config::DISTANCE_MIN_CM || cm > Config::DISTANCE_MAX_CM) {
        return;
    }

    // Add to rolling sample buffer
    samples[cursor] = cm;
    cursor = (cursor + 1) % 5;
    if (count < 5) count++;

    // Median filter to eliminate surface noise and air bubbles
    float sorted[5];
    for (uint8_t i = 0; i < count; i++) sorted[i] = samples[i];
    for (uint8_t i = 0; i < count; i++) {
        for (uint8_t j = i + 1; j < count; j++) {
            if (sorted[j] < sorted[i]) {
                float t = sorted[i];
                sorted[i] = sorted[j];
                sorted[j] = t;
            }
        }
    }

    current.cm = sorted[count / 2];
    current.valid = (count >= 2);
}

DistanceReading UltrasonicSensor::reading() const {
    return current;
}
