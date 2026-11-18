#include <Arduino.h>
#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>

// Camera pin definition for Generic Dual Type-C ESP32-S3-CAM (N16R8) with OV2640
#define CAMERA_PWDN_GPIO   -1
#define CAMERA_RESET_GPIO  -1
#define CAMERA_XCLK_GPIO   15
#define CAMERA_SIOD_GPIO    4
#define CAMERA_SIOC_GPIO    5

#define CAMERA_D7_GPIO      9  // Y9
#define CAMERA_D6_GPIO     16  // Y8
#define CAMERA_D5_GPIO     18  // Y7
#define CAMERA_D4_GPIO     17  // Y6
#define CAMERA_D3_GPIO      8  // Y5
#define CAMERA_D2_GPIO     11  // Y4
#define CAMERA_D1_GPIO     12  // Y3
#define CAMERA_D0_GPIO     10  // Y2

#define CAMERA_VSYNC_GPIO   6
#define CAMERA_HREF_GPIO    7
#define CAMERA_PCLK_GPIO   13

const char *WIFI_SSID = "Airtel_AP Wifi";
const char *WIFI_PASS = "Sdr@3232";

WebServer server(80);
bool cameraReady = false;

void setup() {
    Serial.begin(115200);
    delay(2000); // Allow native USB CDC to establish
    Serial.println("\n\n========================================");
    Serial.println("  SWACHH-NAYAN: CAMERA DIAGNOSTIC TEST  ");
    Serial.println("========================================");

    // 1. Check PSRAM
    if (psramFound()) {
        Serial.printf("[PSRAM] Found! Total: %u KB, Free: %u KB\n",
            (unsigned)(ESP.getPsramSize() / 1024),
            (unsigned)(ESP.getFreePsram() / 1024));
    } else {
        Serial.println("[PSRAM] WARNING: PSRAM not found! Camera requires PSRAM for high-res JPEG buffers.");
    }

    // 2. Configure Camera
    camera_config_t config{};
    config.pin_pwdn = CAMERA_PWDN_GPIO;
    config.pin_reset = CAMERA_RESET_GPIO;
    config.pin_xclk = CAMERA_XCLK_GPIO;
    config.pin_sccb_sda = CAMERA_SIOD_GPIO;
    config.pin_sccb_scl = CAMERA_SIOC_GPIO;
    config.pin_d7 = CAMERA_D7_GPIO;
    config.pin_d6 = CAMERA_D6_GPIO;
    config.pin_d5 = CAMERA_D5_GPIO;
    config.pin_d4 = CAMERA_D4_GPIO;
    config.pin_d3 = CAMERA_D3_GPIO;
    config.pin_d2 = CAMERA_D2_GPIO;
    config.pin_d1 = CAMERA_D1_GPIO;
    config.pin_d0 = CAMERA_D0_GPIO;
    config.pin_vsync = CAMERA_VSYNC_GPIO;
    config.pin_href = CAMERA_HREF_GPIO;
    config.pin_pclk = CAMERA_PCLK_GPIO;
    config.xclk_freq_hz = 20000000;
    config.ledc_timer = LEDC_TIMER_0;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size = FRAMESIZE_QVGA; // 320x240
    config.jpeg_quality = 12;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
    config.fb_location = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;

    Serial.println("[CAMERA] Initializing OV2640 driver...");
    esp_err_t err = esp_camera_init(&config);
    if (err == ESP_OK) {
        cameraReady = true;
        Serial.println("[CAMERA] SUCCESS: Camera initialized successfully!");

        sensor_t *s = esp_camera_sensor_get();
        if (s) {
            Serial.printf("[CAMERA] Sensor PID: 0x%02X (OV2640=0x26, OV3660=0x36, OV5640=0x56)\n", s->id.PID);
            // Flip image if mounted inverted
            s->set_vflip(s, 1);
            s->set_hmirror(s, 0);
        }
    } else {
        cameraReady = false;
        Serial.printf("[CAMERA] ERROR: esp_camera_init failed with code 0x%04X (%s)\n", err, esp_err_to_name(err));
    }

    // 3. Test capture
    if (cameraReady) {
        Serial.println("[CAMERA] Capturing test frame...");
        camera_fb_t *fb = esp_camera_fb_get();
        if (fb) {
            Serial.printf("[CAMERA] FRAME CAPTURED! Length: %u bytes, Format: JPEG, Dimensions: %ux%u\n",
                (unsigned)fb->len, (unsigned)fb->width, (unsigned)fb->height);
            esp_camera_fb_return(fb);
        } else {
            Serial.println("[CAMERA] ERROR: Frame capture returned NULL.");
        }
    }

    // 4. Start Wi-Fi and snapshot server
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.printf("[WIFI] Connecting to '%s'...\n", WIFI_SSID);
    uint32_t t0 = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t0 < 8000) {
        delay(500);
        Serial.print(".");
    }
    Serial.println();

    if (WiFi.status() == WL_CONNECTED) {
        Serial.print("[WIFI] Connected! IP Address: http://");
        Serial.println(WiFi.localIP());

        server.on("/", HTTP_GET, []() {
            String html = "<!doctype html><html><head><title>Camera Test</title><meta name='viewport' content='width=device-width,initial-scale=1'></head>"
                          "<body style='background:#111;color:#eee;text-align:center;font-family:sans-serif;padding:20px;'>"
                          "<h2>Swachh-Nayan: Live Camera View</h2>"
                          "<p><img id='cam' src='/snapshot' style='max-width:90%;border:2px solid #5de0a0;border-radius:8px;' /></p>"
                          "<p><button onclick=\"document.getElementById('cam').src='/snapshot?t='+Date.now()\" style='padding:10px 20px;font-size:16px;background:#5de0a0;color:#000;border:none;border-radius:6px;cursor:pointer;'>Refresh Snapshot</button></p>"
                          "<script>setInterval(function(){ document.getElementById('cam').src='/snapshot?t='+Date.now(); }, 2000);</script>"
                          "</body></html>";
            server.send(200, "text/html", html);
        });

        server.on("/snapshot", HTTP_GET, []() {
            if (!cameraReady) {
                server.send(503, "text/plain", "Camera not ready");
                return;
            }
            camera_fb_t *fb = esp_camera_fb_get();
            if (!fb) {
                server.send(500, "text/plain", "Capture failed");
                return;
            }
            server.sendHeader("Access-Control-Allow-Origin", "*");
            server.sendHeader("Cache-Control", "no-cache");
            WiFiClient client = server.client();
            String header = "HTTP/1.1 200 OK\r\nContent-Type: image/jpeg\r\nContent-Length: " + String(fb->len) + "\r\nConnection: close\r\n\r\n";
            client.write((const uint8_t*)header.c_str(), header.length());
            client.write(fb->buf, fb->len);
            esp_camera_fb_return(fb);
        });

        server.begin();
        Serial.println("[SERVER] View camera at http://" + WiFi.localIP().toString());
    } else {
        Serial.println("[WIFI] Wi-Fi not connected (or timed out). USB Serial testing active.");
    }
}

void loop() {
    server.handleClient();
    static uint32_t lastCheck = 0;
    if (millis() - lastCheck >= 3000) {
        lastCheck = millis();
        if (cameraReady) {
            camera_fb_t *fb = esp_camera_fb_get();
            if (fb) {
                Serial.printf("[HEARTBEAT] Camera OK: %u bytes captured (Heap: %u KB free, PSRAM: %u KB free)\n",
                    (unsigned)fb->len,
                    (unsigned)(ESP.getFreeHeap() / 1024),
                    (unsigned)(ESP.getFreePsram() / 1024));
                esp_camera_fb_return(fb);
            } else {
                Serial.println("[HEARTBEAT] Camera ERROR: Frame capture failed.");
            }
        } else {
            Serial.println("[HEARTBEAT] Camera NOT READY.");
        }
    }
}
