#include <Arduino.h>
#include "esp_camera.h"
#include "config.h"
#include "sensor_ultrasonic.h"
#include "sensor_water.h"
#include "camera_manager.h"
#include "ai_inference.h"
#include "decision_engine.h"
#include "display_manager.h"
#include "actuator_manager.h"
#include "diagnostics.h"
#include "web_dashboard.h"
#include "sd_card_manager.h"

#if !MOCK_MODE
#include <Wire.h>
#endif

static UltrasonicSensor ultrasonic;
static WaterSensor water;
static CameraManager camera;
static AIInference ai;
static DecisionEngine decisions;
static DisplayManager display;
static ActuatorManager actuator;
static Diagnostics diagnostics;
static WebDashboard dashboard;
static SDCardManager sdCard;
static Prediction prediction{};
static uint32_t lastCamera = 0;
static uint32_t lastSdLog = 0;
static uint32_t lastSnapSave = 0;
static CameraStatus cameraStatus{false, false, 0, 0, "NOT_STARTED"};
static bool manualRequest = false;

static uint32_t trashCount = 0;
static bool prevServo = false;

static void statusLine() {
#if MOCK_MODE
    char line[160];
    snprintf(line, sizeof(line), "STATE=%s CAMERA=UNAVAILABLE AI=UNKNOWN (MOCK MODE) SERVO=%s SD=%s\n",
        DecisionEngine::name(decisions.state()),
        actuator.active() ? "ACTIVE" : "SAFE",
        sdCard.isMounted() ? "MOUNTED" : "UNAVAILABLE");
    Serial.print(line);
#else
    auto d = ultrasonic.reading();
    auto w = water.reading();
    auto s = sdCard.getStatus();
    char line[220];
    snprintf(line, sizeof(line), "STATE=%s DIST=%.1fcm WATER=%s(raw:%d) CAMERA=%s AI=%s %.2f SERVO=%s SD=%s (%uMB free)\n",
        DecisionEngine::name(decisions.state()),
        d.valid ? d.cm : 0.0f,
        !w.valid ? "UNAVAILABLE" : (w.wet ? "WET" : "DRY"),
        (int)w.raw,
        camera.available() ? "READY" : "UNAVAILABLE",
        prediction.label, prediction.confidence,
        actuator.active() ? "ACTIVE" : "SAFE",
        s.mounted ? "MOUNTED" : "NO_CARD",
        s.mounted ? (s.totalMB - s.usedMB) : 0);
    Serial.print(line);
#endif
}

static void mockScenario(String name) {
#if MOCK_MODE
    static const char *expected = "MONITORING";
    Prediction p = ai.mockPrediction("UNKNOWN", 0);
    DistanceReading d{100, true, millis()};
    WaterReading w{1094, true, false, millis()};
    bool camReady = false, camFault = false, manual = false;
    if (name == "waste") { p = ai.mockPrediction("VISIBLE_WASTE", 0.91f); expected = "WASTE_DETECTED"; }
    else if (name == "low_conf") { p = ai.mockPrediction("VISIBLE_WASTE", 0.31f); expected = "MONITORING"; }
    else if (name == "camera_fail") { camFault = true; expected = "CAMERA_FAULT"; }
    else if (name == "sensor_fault") { d.valid = false; expected = "SENSOR_FAULT"; }
    else if (name == "wet") { w.wet = true; expected = "MONITORING"; }
    else if (name == "obstruction") { d.cm = 10; for (uint8_t i = 0; i < Config::CONFIRM_COUNT; i++) decisions.update(d, w, false, false, p, false); expected = "POSSIBLE_OBSTRUCTION"; }
    else if (name != "safe") { Serial.println("Unknown scenario"); return; }
    Decision out = decisions.update(d, w, camReady, camFault, p, manual);
    Serial.printf("MOCK_SCENARIO=%s EXPECTED=%s ACTUAL=%s MOCK_PREDICTION=%s CONF=%.2f SERVO_REQUEST=%s\n",
        name.c_str(), expected, DecisionEngine::name(out.state), p.label, p.confidence, out.servoRequest ? "YES" : "NO");
#else
    (void)name;
    Serial.println("scenario commands are available only in MOCK_MODE");
#endif
}

#if MOCK_MODE
static void runSelfTest() {
    struct Case { const char *name; bool distValid; float cm; bool camReady; bool camFault; bool predValid; float confidence; bool waterValid; SystemState expected; };
    const Case cases[] = {
        {"safe", true, 100, false, false, false, 0, true, SystemState::MONITORING},
        {"waste_test_injection", true, 100, true, false, true, 0.91f, true, SystemState::WASTE_DETECTED},
        {"camera_fault", true, 100, false, true, false, 0, true, SystemState::CAMERA_FAULT},
        {"low_confidence", true, 100, true, false, true, 0.2f, true, SystemState::MONITORING},
        {"sensor_fault", false, 100, false, false, false, 0, true, SystemState::SENSOR_FAULT},
        {"possible_obstruction", true, 10, false, false, false, 0, true, SystemState::POSSIBLE_OBSTRUCTION}
    };
    uint8_t passed = 0;
    for (const auto &t : cases) {
        decisions.begin();
        DistanceReading d{t.cm, t.distValid, millis()};
        WaterReading w{1000, t.waterValid, false, millis()};
        Prediction p{};
        strlcpy(p.label, t.predValid ? "TEST_ONLY" : "UNKNOWN", sizeof(p.label));
        p.valid = t.predValid; p.confidence = t.confidence; p.mock = false;
        Decision out{};
        uint8_t repeats = (String(t.name) == "possible_obstruction") ? Config::CONFIRM_COUNT : 1;
        for (uint8_t i = 0; i < repeats; i++) out = decisions.update(d, w, t.camReady, t.camFault, p, false);
        bool ok = out.state == t.expected;
        Serial.printf("SELFTEST %s expected=%s actual=%s %s\n", t.name, DecisionEngine::name(t.expected), DecisionEngine::name(out.state), ok ? "PASS" : "FAIL");
        if (ok) passed++;
    }
    Serial.printf("SELFTEST_RESULT %u/%u passed.\n", passed, (unsigned)(sizeof(cases) / sizeof(cases[0])));
    decisions.begin();
}
#endif

static void handleCommand(String line, Stream& port) {
    line.trim();
    if (line == "help") {
        const char* h = "Commands: help | status | sd | snap | frame | calibrate dry|wet | manual divert|safe\n";
        port.print(h);
    } else if (line == "status") {
        statusLine();
    } else if (line == "frame" || line == "get_frame") {
        CameraStatus cs = camera.capture(millis());
        cameraStatus = cs;
        if (cs.frameValid && camera.frameData()) {
            port.printf("IMG_START:%u\n", (unsigned)cs.frameBytes);
            port.write(camera.frameData(), cs.frameBytes);
            port.print("\nIMG_END\n");
            camera.releaseFrame();
            display.reclaimBus();
        } else {
            camera.releaseFrame();
            display.reclaimBus();
            port.println("IMG_FAIL:NO_FRAME");
        }
        auto d = ultrasonic.reading();
        auto w = water.reading();
        display.update(millis(), d, w, cameraStatus, prediction, decisions.state(), actuator.active());
    } else if (line == "sd") {
        auto s = sdCard.getStatus();
        char buf[160];
        snprintf(buf, sizeof(buf), "SD: mounted=%s total=%uMB used=%uMB snapshots=%u error=%s\n",
            s.mounted ? "YES" : "NO", (unsigned)s.totalMB, (unsigned)s.usedMB, (unsigned)s.snapshotsSaved, s.lastError);
        port.print(buf);
    } else if (line == "snap") {
        CameraStatus cs = camera.capture(millis());
        if (cs.frameValid) {
            bool saved = sdCard.saveSnapshot(camera.frameData(), cs.frameBytes, "manual");
            char buf[120];
            snprintf(buf, sizeof(buf), "Snapshot captured (%u bytes) -> SD save: %s\n", (unsigned)cs.frameBytes, saved ? "SUCCESS" : "FAILED");
            port.print(buf);
            camera.releaseFrame();
        } else {
            char buf[80];
            snprintf(buf, sizeof(buf), "Snapshot failed: %s\n", cs.error);
            port.print(buf);
        }
    }
#if MOCK_MODE
    else if (line == "selftest") runSelfTest();
#endif
    else if (line.startsWith("scenario ")) mockScenario(line.substring(9));
    else if (line == "calibrate dry") water.calibrateDry();
    else if (line == "calibrate wet") water.calibrateWet();
    else if (line == "pins") {
        int a3 = analogRead(Config::PIN_WATER_ANALOG);
        port.printf("WATER_SENSOR: GPIO3_RAW=%d FILTERED_RAW=%d WET=%s\n", a3, (int)water.reading().raw, water.reading().wet ? "YES" : "NO");
    }
    else if (line == "scan_i2c") {
        const int testPairs[][2] = { {1, 2}, {8, 9}, {2, 1}, {9, 8} };
        for (auto& p : testPairs) {
            Wire.end();
            delay(10);
            Wire.begin(p[0], p[1], 100000);
            delay(10);
            port.printf("SCAN_I2C SDA=%d SCL=%d:", p[0], p[1]);
            bool found = false;
            for (uint8_t a = 8; a < 120; a++) {
                Wire.beginTransmission(a);
                if (Wire.endTransmission() == 0) {
                    port.printf(" 0x%02X", a);
                    found = true;
                }
            }
            if (!found) port.print(" NONE");
            port.println();
        }
        display.reclaimBus();
    }
    else if (line == "manual divert" || line == "fire" || line == "fire_2x") {
        actuator.trigger2xSweep(millis());
        port.println("FIRE_2X_TRIGGERED");
    }
    else if (line.startsWith("servo ")) {
        int ang = line.substring(6).toInt();
        actuator.moveTo(ang, millis());
        port.printf("SERVO_CMD:%d\n", ang);
    }
    else if (line == "manual safe" || line == "servo_safe") {
        actuator.moveTo(Config::SERVO_SAFE_DEG, millis());
        port.printf("SERVO_SAFE:%d\n", Config::SERVO_SAFE_DEG);
    }
    else if (line == "sweep") {
        port.println("SWEEP_START");
        int testAngles[] = { 90, 45, 0, 45, 90, 135, 180, 90 };
        for (int a : testAngles) {
            actuator.moveTo(a, millis());
            port.printf("SWEEP_ANGLE:%d\n", a);
            delay(750);
        }
        port.println("SWEEP_DONE");
    }
    else if (line.length()) {
        port.println("Unknown command. Type 'help'.");
    }
}

static void commands() {
    static String line;
    while (Serial.available()) {
        char c = Serial.read();
        if (c == '\r') continue;
        if (c == '\n') {
            handleCommand(line, Serial);
            line = "";
        } else if (line.length() < 80) line += c;
    }
}

void setup() {
    Serial.begin(Config::SERIAL_BAUD);
    delay(200);
    Serial.println("--- SWACHH NAYAN BOOTING ---");
    diagnostics.begin();
    decisions.begin();
    prediction = ai.mockPrediction("UNKNOWN", 0);
    dashboard.begin();

#if MOCK_MODE
    Serial.println("Swachh-Nayan MOCK_MODE active. Sensor values and predictions are simulated. Type 'help'.");
#else
    // 1. Initialize camera first (tri-states OV3660 bus lines on GPIO 8 & 9)
    bool camOk = camera.begin();
    cameraStatus = {camOk, false, 0, millis(), camOk ? "OK" : "CAMERA_UNAVAILABLE"};

    // 2. Initialize display (I2C) now that bus is free
    display.begin();
    display.reclaimBus();

    // 3. Initialize sensors
    ultrasonic.begin(Config::PIN_TRIG, Config::PIN_ECHO);
    bool adcOk = water.begin();
    bool sdOk = sdCard.begin();
    actuator.begin();

    diagnostics.log(adcOk ? "INFO" : "ERROR", adcOk ? "ADS1115 ready" : "ADS1115 unavailable");
    diagnostics.log(camOk ? "INFO" : "WARN", camOk ? "Camera ready (OV3660)" : "Camera unavailable");
    diagnostics.log(sdOk ? "INFO" : "WARN", sdOk ? "MicroSD ready" : "MicroSD not mounted / no card");

    Serial.println("Swachh-Nayan Hardware Drivers Initialized.");
    lastCamera = millis();
#endif
}

void loop() {
    uint32_t now = millis();
    commands();

#if !MOCK_MODE
    ultrasonic.update(now);
    water.update(now);

    if (now - lastCamera >= Config::CAMERA_PERIOD_MS) {
        lastCamera = now;
        CameraStatus cs = camera.capture(now);
        cameraStatus = cs;
        if (cs.frameValid && camera.frameData()) {
            prediction = ai.infer(camera.frameData(), cs.frameBytes);
            prediction.valid = true;
            camera.releaseFrame();
            display.reclaimBus();
        }
    }

    auto d = ultrasonic.reading();
    auto w = water.reading();
    Decision dec = decisions.update(d, w, camera.available(), cameraStatus.ready && !cameraStatus.frameValid, prediction, manualRequest);
    if (dec.servoRequest) actuator.requestMove(true, now);
    manualRequest = false;
    actuator.update(now);

    bool curServo = actuator.active();
    if (curServo && !prevServo) trashCount++;
    prevServo = curServo;

    display.update(now, d, w, cameraStatus, prediction, dec.state, curServo);

    // Stream live telemetry to Laptop Live Studio via COM8
    static uint32_t lastTelem = 0;
    if (now - lastTelem >= 350) {
        lastTelem = now;
        char tb[190];
        snprintf(tb, sizeof(tb), "TELEMETRY:{\"dist\":%.1f,\"state\":\"%s\",\"water\":\"%s\",\"raw\":%d,\"servo\":%d,\"angle\":%d,\"trash\":%u}\n",
                 d.valid ? d.cm : 0.0f,
                 DecisionEngine::name(dec.state),
                 w.valid ? (w.wet ? "WET" : "DRY") : "DRY",
                 (int)w.raw,
                 curServo ? 1 : 0,
                 actuator.currentAngle(),
                 (unsigned)trashCount);
        Serial.print(tb);
    }

    // Periodic telemetry log to SD card
    if (now - lastSdLog >= Config::TELEMETRY_LOG_PERIOD_MS) {
        lastSdLog = now;
        sdCard.logTelemetry(now, d.cm, d.valid, w.raw, w.wet, w.valid, DecisionEngine::name(dec.state), prediction.label, prediction.confidence);
    }

    DashboardData snapshot;
    snapshot.mode = "DEVICE";
    snapshot.state = dec.state;
    snapshot.distance = d;
    snapshot.water = w;
    snapshot.waterCalibrated = water.calibrated();
    snapshot.camera = cameraStatus;
    snapshot.prediction = prediction;
    snapshot.sdCard = sdCard.getStatus();
    snapshot.servoActive = actuator.active();
    snapshot.actuatorEnabled = Config::ACTUATOR_ENABLED;
    snapshot.freeHeap = ESP.getFreeHeap();
    snapshot.uptimeMs = now;
    dashboard.update(snapshot);
#else
    DashboardData snapshot;
    snapshot.mode = "MOCK";
    snapshot.state = decisions.state();
    snapshot.distance = {100.0f, true, now};
    snapshot.water = {1094, true, false, now};
    snapshot.waterCalibrated = false;
    snapshot.camera = {false, false, 0, now, "MOCK_NO_CAMERA"};
    snapshot.prediction = ai.mockPrediction("MOCK_NO_RESULT", 0.0f);
    snapshot.sdCard = {false, 0, 0, 0, "MOCK_SD_DISABLED"};
    snapshot.servoActive = false;
    snapshot.actuatorEnabled = false;
    snapshot.freeHeap = ESP.getFreeHeap();
    snapshot.uptimeMs = now;
    dashboard.update(snapshot);
#endif

    dashboard.loop();
    diagnostics.heartbeat(now);
}
