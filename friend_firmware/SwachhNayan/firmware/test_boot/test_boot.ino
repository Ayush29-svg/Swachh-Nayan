#include <Arduino.h>

void setup() {
    Serial.begin(115200);
    delay(2000);
    Serial.println("--- BOOT TEST START ---");
    Serial.printf("Chip Model: %s, Cores: %d, Rev: %d\n", ESP.getChipModel(), ESP.getChipCores(), ESP.getChipRevision());
    Serial.printf("Flash Size: %u MB\n", (unsigned)(ESP.getFlashChipSize() / (1024 * 1024)));
    Serial.printf("PSRAM Found: %s\n", psramFound() ? "YES" : "NO");
    if (psramFound()) {
        Serial.printf("PSRAM Size: %u KB, Free: %u KB\n", (unsigned)(ESP.getPsramSize() / 1024), (unsigned)(ESP.getFreePsram() / 1024));
    }
    Serial.printf("Heap Free: %u KB\n", (unsigned)(ESP.getFreeHeap() / 1024));
    Serial.println("--- BOOT TEST END ---");
}

void loop() {
    Serial.println("ESP32-S3 IS ALIVE!");
    delay(1500);
}
