#include <Arduino.h>
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

static void statusLine() {
#if MOCK_MODE
    Serial.printf("STATE=%s CAMERA=UNAVAILABLE AI=UNKNOWN (MOCK MODE) SERVO=%s SD=%s\n",
        DecisionEngine::name(decisions.state()),
        actuator.active() ? "ACTIVE" : "SAFE",
        sdCard.isMounted() ? "MOUNTED" : "UNAVAILABLE");
#else
    auto d = ultrasonic.reading();
    auto w = water.reading();
    auto s = sdCard.getStatus();
    Serial.printf("STATE=%s DIST=", DecisionEngine::name(decisions.state()));
    if (d.valid) Serial.printf("%.1fcm", d.cm); else Serial.print("UNAVAILABLE");
    Serial.print(" WATER=");
    if (!w.valid) Serial.print("UNAVAILABLE"); else Serial.print(w.wet ? "WET" : "DRY/UNCALIBRATED");
    Serial.printf(" CAMERA=%s AI=%s %.2f SERVO=%s SD=%s (%uMB free)\n",
        camera.available() ? "READY" : "UNAVAILABLE",
        prediction.label, prediction.confidence,
        actuator.active() ? "ACTIVE" : "SAFE",
        s.mounted ? "MOUNTED" : "NO_CARD",
        s.mounted ? (s.totalMB - s.usedMB) : 0);
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
        bool ok = out.state == t.expected && !out.servoRequest;
        Serial.printf("SELFTEST %s expected=%s actual=%s %s\n", t.name, DecisionEngine::name(t.expected), DecisionEngine::name(out.state), ok ? "PASS" : "FAIL");
        if (ok) passed++;
    }
    Serial.printf("SELFTEST_RESULT %u/%u passed.\n", passed, (unsigned)(sizeof(cases) / sizeof(cases[0])));
    decisions.begin();
}
#endif

static void commands() {
    static String line;
    while (Serial.available()) {
        char c = Serial.read();
        if (c == '\r') continue;
        if (c == '\n') {
            line.trim();
            if (line == "help") {
                Serial.println("Commands: help | status | sd | snap | calibrate dry|wet | manual divert|safe | selftest (mock) | scenario ...");
            } else if (line == "status") {
                statusLine();
            } else if (line == "sd") {
                auto s = sdCard.getStatus();
                Serial.printf("SD: mounted=%s total=%uMB used=%uMB snapshots=%u error=%s\n",
                    s.mounted ? "YES" : "NO", (unsigned)s.totalMB, (unsigned)s.usedMB, (unsigned)s.snapshotsSaved, s.lastError);
            } else if (line == "snap") {
                CameraStatus cs = camera.capture(millis());
                if (cs.frameValid) {
                    bool saved = sdCard.saveSnapshot(camera.frameData(), cs.frameBytes, "manual");
                    Serial.printf("Snapshot captured (%u bytes) -> SD save: %s\n", (unsigned)cs.frameBytes, saved ? "SUCCESS" : "FAILED");
                    camera.releaseFrame();
                } else {
                    Serial.printf("Snapshot failed: %s\n", cs.error);
                }
            }
#if MOCK_MODE
            else if (line == "selftest") runSelfTest();
#endif
            else if (line.startsWith("scenario ")) mockScenario(line.substring(9));
            else if (line == "calibrate dry") water.calibrateDry();
            else if (line == "calibrate wet") water.calibrateWet();
            else if (line == "manual divert") manualRequest = true;
            else if (line == "manual safe") actuator.requestMove(false, millis());
            else if (line.length()) Serial.println("Unknown command. Type 'help'.");
            line = "";
        } else if (line.length() < 80) line += c;
    }
}

void setup() {
    Serial.begin(Config::SERIAL_BAUD);
    delay(100);
    diagnostics.begin();
    decisions.begin();
    prediction = ai.mockPrediction("UNKNOWN", 0);
    dashboard.begin();

#if MOCK_MODE
    Serial.println("Swachh-Nayan MOCK_MODE active. Sensor values and predictions are simulated. Type 'help'.");
#else
    Wire.begin(Config::PIN_SDA, Config::PIN_SCL);
    ultrasonic.begin(Config::PIN_TRIG, Config::PIN_ECHO);
    bool adcOk = water.begin();
    display.begin();
    bool camOk = camera.begin();
    cameraStatus = {camOk, false, 0, millis(), camOk ? "OK" : "CAMERA_UNAVAILABLE"};
    bool sdOk = sdCard.begin();
    actuator.begin();

    diagnostics.log(adcOk ? "INFO" : "ERROR", adcOk ? "ADS1115 ready" : "ADS1115 unavailable");
    diagnostics.log(camOk ? "INFO" : "WARN", camOk ? "Camera ready (OV2640)" : "Camera unavailable");
    diagnostics.log(sdOk ? "INFO" : "WARN", sdOk ? "MicroSD ready" : "MicroSD not mounted / no card");

    Serial.println("Swachh-Nayan Hardware Drivers Initialized.");
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
        if (cs.frameValid) {
            prediction = ai.infer(camera.frameData(), cs.frameBytes);
            // Save snapshot to SD card on alert states
            if ((decisions.state() == SystemState::WASTE_DETECTED || decisions.state() == SystemState::POSSIBLE_OBSTRUCTION) && (now - lastSnapSave > 10000)) {
                lastSnapSave = now;
                sdCard.saveSnapshot(camera.frameData(), cs.frameBytes, DecisionEngine::name(decisions.state()));
            }
            camera.releaseFrame();
        } else {
            prediction.valid = false;
            strlcpy(prediction.label, cs.error, sizeof(prediction.label));
        }
    }

    auto d = ultrasonic.reading();
    auto w = water.reading();
    Decision dec = decisions.update(d, w, camera.available(), cameraStatus.ready && !cameraStatus.frameValid, prediction, manualRequest);
    if (dec.servoRequest) actuator.requestMove(true, now);
    manualRequest = false;
    actuator.update(now);
    display.update(now, d, w, cameraStatus, prediction, dec.state, actuator.active());

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
