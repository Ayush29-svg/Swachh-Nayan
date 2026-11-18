#include "web_dashboard.h"
#include "config.h"
#include "dashboard_html.h"

#if WEB_DASHBOARD_ENABLED
#include <WiFi.h>
#include <WebServer.h>

#if CAMERA_ENABLED
#include "esp_camera.h"
#endif

static WebServer server(80);

static String clean(const char *s) {
    String o;
    if (!s) return o;
    while (*s) {
        char c = *s++;
        if ((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.' || c == ' ') {
            o += c;
        }
    }
    return o;
}
#endif

bool WebDashboard::begin() {
#if WEB_DASHBOARD_ENABLED
    if (strlen(Config::WIFI_SSID) == 0) {
        Serial.println("Dashboard disabled: set WIFI_SSID in config.h");
        return false;
    }
    WiFi.mode(WIFI_STA);
    WiFi.begin(Config::WIFI_SSID, Config::WIFI_PASSWORD);
    wifiStarted = true;
    Serial.println("Connecting dashboard Wi-Fi in background...");
    return true;
#else
    Serial.println("Dashboard server disabled in config.h");
    return false;
#endif
}

void WebDashboard::update(const DashboardData &d) {
    current = d;
#if WEB_DASHBOARD_ENABLED
    if (WiFi.status() == WL_CONNECTED) {
        current.wifiRssi = WiFi.RSSI();
    }
#endif
}

void WebDashboard::loop() {
#if WEB_DASHBOARD_ENABLED
    if (wifiStarted && !isOnline) {
        if (WiFi.status() == WL_CONNECTED) {
            server.on("/", HTTP_GET, []() {
                server.send_P(200, "text/html", DASHBOARD_HTML);
            });

            server.on("/api/status", HTTP_GET, [this]() {
                const auto &d = current;
                char json[1024];
                String st = clean(DecisionEngine::name(d.state));
                String label = clean(d.prediction.label);
                String err = clean(d.camera.error ? d.camera.error : "NONE");
                String sdErr = clean(d.sdCard.lastError ? d.sdCard.lastError : "NONE");

                snprintf(json, sizeof(json),
                    "{\"mode\":\"%s\",\"state\":\"%s\",\"distanceValid\":%s,\"distanceCm\":%.2f,"
                    "\"waterValid\":%s,\"waterRaw\":%d,\"waterWet\":%s,\"waterCalibrated\":%s,"
                    "\"cameraReady\":%s,\"cameraError\":\"%s\",\"prediction\":\"%s\",\"predictionConfidence\":%.3f,"
                    "\"predictionValid\":%s,\"predictionMock\":%s,\"inferenceMs\":%lu,"
                    "\"sdMounted\":%s,\"sdTotalMB\":%u,\"sdUsedMB\":%u,\"sdSnapshots\":%u,\"sdError\":\"%s\","
                    "\"servoActive\":%s,\"actuatorEnabled\":%s,\"uptimeMs\":%lu,\"freeHeap\":%lu,\"rssi\":%d}",
                    d.mode, st.c_str(),
                    d.distance.valid ? "true" : "false", d.distance.cm,
                    d.water.valid ? "true" : "false", d.water.raw,
                    d.water.wet ? "true" : "false", d.waterCalibrated ? "true" : "false",
                    d.camera.ready ? "true" : "false", err.c_str(),
                    label.c_str(), d.prediction.confidence,
                    d.prediction.valid ? "true" : "false", d.prediction.mock ? "true" : "false",
                    (unsigned long)d.prediction.inferenceMs,
                    d.sdCard.mounted ? "true" : "false", (unsigned)d.sdCard.totalMB, (unsigned)d.sdCard.usedMB,
                    (unsigned)d.sdCard.snapshotsSaved, sdErr.c_str(),
                    d.servoActive ? "true" : "false", d.actuatorEnabled ? "true" : "false",
                    (unsigned long)d.uptimeMs, (unsigned long)d.freeHeap, d.wifiRssi);

                server.sendHeader("Access-Control-Allow-Origin", "*");
                server.send(200, "application/json", json);
            });

#if CAMERA_ENABLED
            server.on("/api/camera/snapshot", HTTP_GET, []() {
                camera_fb_t *fb = esp_camera_fb_get();
                if (!fb) {
                    server.sendHeader("Access-Control-Allow-Origin", "*");
                    server.send(503, "application/json", "{\"error\":\"capture_failed\"}");
                    return;
                }
                server.sendHeader("Access-Control-Allow-Origin", "*");
                server.sendHeader("Cache-Control", "no-cache, no-store, must-revalidate");
                WiFiClient client = server.client();
                String header = "HTTP/1.1 200 OK\r\nContent-Type: image/jpeg\r\nContent-Length: " + String(fb->len) + "\r\nConnection: close\r\n\r\n";
                client.write((const uint8_t*)header.c_str(), header.length());
                client.write(fb->buf, fb->len);
                esp_camera_fb_return(fb);
            });
#endif

            server.onNotFound([]() {
                server.send(404, "application/json", "{\"error\":\"not_found\"}");
            });

            server.begin();
            isOnline = true;
            Serial.print("Dashboard available at: http://");
            Serial.println(WiFi.localIP());
        } else if (millis() > Config::WIFI_CONNECT_TIMEOUT_MS) {
            wifiStarted = false;
            Serial.println("Dashboard Wi-Fi connection timed out; verify credentials in config.h");
        }
    }

    if (isOnline) {
        if (WiFi.status() != WL_CONNECTED) {
            isOnline = false;
            Serial.println("Dashboard Wi-Fi disconnected");
        } else {
            server.handleClient();
        }
    }
#endif
}
