/*
 * SWACHH NAYAN — ESP32-S3-CAM (N16R8) Master Sensor & Actuator Controller
 * 
 * Hardware Pinout (ESP32-S3-CAM):
 * - Ultrasonic Sensor:  TRIG -> GPIO 47, ECHO -> GPIO 48 (via 1k/2k divider)
 * - MG996R Servo Flap:  PWM  -> GPIO 21
 * - 12V Pump Relay:     IN   -> GPIO 4
 * - 16x2 I2C LCD:       SDA  -> GPIO 1,  SCL  -> GPIO 2
 * - Camera:             Built-in OV2640 / OV3660 DVP Parallel Ribbon
 * 
 * Communication:
 * - Emits JSON telemetry over USB Serial (COM5) @ 115200 baud
 * - Receives commands over USB Serial:
 *     CMD:DIVERT
 *     CMD:PUMP:ON / CMD:PUMP:OFF
 *     CMD:SERVO:<angle>
 *     CMD:RESET_COUNT
 *     CMD:LCD:<line1>|<line2>
 */

#include <Arduino.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <ESP32Servo.h>
#include "esp_camera.h"

// ==========================================
// 1. PIN CONFIGURATIONS
// ==========================================
#define PIN_SERVO        21
#define PIN_RELAY_PUMP    4
#define PIN_I2C_SDA       1
#define PIN_I2C_SCL       2
#define PIN_US_TRIG      47
#define PIN_US_ECHO      48

// Camera Pinout for ESP32-S3-CAM
#define PWDN_GPIO_NUM    -1
#define RESET_GPIO_NUM   -1
#define XCLK_GPIO_NUM    10
#define SIOD_GPIO_NUM    40
#define SIOC_GPIO_NUM    39
#define Y9_GPIO_NUM      46
#define Y8_GPIO_NUM      45
#define Y7_GPIO_NUM      42
#define Y6_GPIO_NUM      41
#define Y5_GPIO_NUM      38
#define Y4_GPIO_NUM      18
#define Y3_GPIO_NUM      17
#define Y2_GPIO_NUM      16
#define VSYNC_GPIO_NUM   20
#define HREF_GPIO_NUM    19
#define PCLK_GPIO_NUM    11

// Calibration Constants
const float DRAIN_MAX_DEPTH_CM = 30.0;   // Distance when empty
const float CRITICAL_FLOOD_CM   = 10.0;   // Distance threshold for overflow alert

// Peripherals
LiquidCrystal_I2C lcd(0x27, 16, 2);
Servo gateServo;

// State Variables
struct DeviceState {
  float distance_cm = 25.0;
  float water_depth_cm = 5.0;
  float water_percentage = 16.7;
  bool pump_status = false;
  bool auto_pump_enabled = true;
  String gate_status = "NORMAL";
  float servo_angle = 0.0;
  int trash_count = 0;
  bool camera_online = false;
  unsigned long last_telemetry_time = 0;
  unsigned long last_sensor_time = 0;
  unsigned long divert_start_time = 0;
  bool is_diverting = false;
} state;

// ==========================================
// 2. HARDWARE MEASUREMENTS & CONTROLS
// ==========================================
float readUltrasonic() {
  digitalWrite(PIN_US_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_US_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_US_TRIG, LOW);

  unsigned long duration = pulseIn(PIN_US_ECHO, HIGH, 25000); // 25ms timeout (~4m)
  if (duration == 0) return state.distance_cm; // Hold last known reading on timeout

  float distance = (duration * 0.0343f) / 2.0f;
  if (distance < 2.0f || distance > 400.0f) return state.distance_cm;
  return distance;
}

void setServoAngle(float angle) {
  angle = constrain(angle, 0.0f, 180.0f);
  state.servo_angle = angle;
  gateServo.write((int)angle);
}

void setPump(bool on) {
  state.pump_status = on;
  digitalWrite(PIN_RELAY_PUMP, on ? HIGH : LOW);
}

void startDiverter() {
  state.gate_status = "DIVERTING";
  state.is_diverting = true;
  state.divert_start_time = millis();
  setServoAngle(90.0f); // Divert angle
  state.trash_count++;
}

void updateLCDDisplay(String l1 = "", String l2 = "") {
  if (l1 == "" && l2 == "") {
    lcd.setCursor(0, 0);
    lcd.print("SWACHH-NAYAN S3 ");
    lcd.setCursor(0, 1);
    char buf[17];
    snprintf(buf, sizeof(buf), "D:%2dcm T:%d P:%s", 
             (int)state.distance_cm, 
             state.trash_count, 
             state.pump_status ? "ON " : "OFF");
    lcd.print(buf);
  } else {
    lcd.setCursor(0, 0);
    lcd.print("                ");
    lcd.setCursor(0, 0);
    lcd.print(l1.substring(0, 16));
    lcd.setCursor(0, 1);
    lcd.print("                ");
    lcd.setCursor(0, 1);
    lcd.print(l2.substring(0, 16));
  }
}

// ==========================================
// 3. CAMERA SETUP (Supports OV2640 & OV3660)
// ==========================================
bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  
  // 10MHz safe frequency for both OV2640 and OV3660 stability
  config.xclk_freq_hz = 10000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size   = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  config.fb_count     = 2;
  config.fb_location  = CAMERA_FB_IN_PSRAM;
  config.grab_mode    = CAMERA_GRAB_LATEST;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    // Fallback: try 16MHz SVGA
    config.xclk_freq_hz = 16000000;
    config.frame_size = FRAMESIZE_SVGA;
    err = esp_camera_init(&config);
  }
  return (err == ESP_OK);
}

// ==========================================
// 4. SERIAL PROTOCOL HANDLER
// ==========================================
void sendTelemetryJSON() {
  Serial.print("TELEMETRY:{");
  Serial.print("\"ultrasonic_distance_cm\":"); Serial.print(state.distance_cm, 1);
  Serial.print(",\"water_depth_cm\":"); Serial.print(state.water_depth_cm, 1);
  Serial.print(",\"water_percentage\":"); Serial.print(state.water_percentage, 1);
  Serial.print(",\"pump_status\":\""); Serial.print(state.pump_status ? "ON" : "OFF"); Serial.print("\"");
  Serial.print(",\"gate_status\":\""); Serial.print(state.gate_status); Serial.print("\"");
  Serial.print(",\"servo_angle\":"); Serial.print(state.servo_angle, 1);
  Serial.print(",\"trash_diverted\":"); Serial.print(state.trash_count);
  Serial.print(",\"camera_online\":"); Serial.print(state.camera_online ? "true" : "false");
  Serial.print(",\"camera_fps\":15.0");
  Serial.println("}");
}

void parseSerialCommand(String cmd) {
  cmd.trim();
  if (cmd == "CMD:DIVERT") {
    startDiverter();
  } else if (cmd == "CMD:PUMP:ON") {
    setPump(true);
  } else if (cmd == "CMD:PUMP:OFF") {
    setPump(false);
  } else if (cmd.startsWith("CMD:SERVO:")) {
    float a = cmd.substring(10).toFloat();
    setServoAngle(a);
  } else if (cmd == "CMD:RESET_COUNT") {
    state.trash_count = 0;
  } else if (cmd.startsWith("CMD:LCD:")) {
    String payload = cmd.substring(8);
    int sep = payload.indexOf('|');
    if (sep != -1) {
      updateLCDDisplay(payload.substring(0, sep), payload.substring(sep + 1));
    }
  }
}

// ==========================================
// 5. MAIN SETUP & LOOP
// ==========================================
void setup() {
  Serial.begin(115200);
  delay(500);

  // 1. Initialize GPIOs
  pinMode(PIN_RELAY_PUMP, OUTPUT);
  setPump(false);

  pinMode(PIN_US_TRIG, OUTPUT);
  pinMode(PIN_US_ECHO, INPUT);

  // 2. Initialize Servo
  ESP32PWM::allocateTimer(0);
  gateServo.setPeriodHertz(50);
  gateServo.attach(PIN_SERVO_PWM, 500, 2500);
  setServoAngle(0.0f);

  // 3. Initialize I2C LCD
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("SWACHH-NAYAN S3");
  lcd.setCursor(0, 1);
  lcd.print("SYSTEM READY");

  // 4. Initialize Camera
  state.camera_online = initCamera();

  Serial.println("\n[SWACHH-NAYAN] ESP32-S3 Master Online. Ready for laptop connection.");
}

void loop() {
  unsigned long now = millis();

  // Read incoming commands from laptop USB
  while (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    parseSerialCommand(cmd);
  }

  // Periodic sensor readings (every 100 ms)
  if (now - state.last_sensor_time >= 100) {
    state.last_sensor_time = now;
    state.distance_cm = readUltrasonic();

    // Calculate water depth based on sensor height
    state.water_depth_cm = max(0.0f, DRAIN_MAX_DEPTH_CM - state.distance_cm);
    state.water_percentage = constrain((state.water_depth_cm / DRAIN_MAX_DEPTH_CM) * 100.0f, 0.0f, 100.0f);

    // Auto-pump protection on critical flood
    if (state.auto_pump_enabled) {
      if (state.distance_cm <= CRITICAL_FLOOD_CM && !state.pump_status) {
        setPump(true);
      } else if (state.distance_cm > (CRITICAL_FLOOD_CM + 5.0f) && state.pump_status) {
        setPump(false);
      }
    }
  }

  // Diverter hold timer (auto return flap to rest after 2.5s)
  if (state.is_diverting && (now - state.divert_start_time >= 2500)) {
    state.is_diverting = false;
    setServoAngle(0.0f);
    state.gate_status = "NORMAL";
  }

  // Periodic Telemetry Transmission to Laptop (every 200 ms)
  if (now - state.last_telemetry_time >= 200) {
    state.last_telemetry_time = now;
    sendTelemetryJSON();
    updateLCDDisplay();
  }
}
