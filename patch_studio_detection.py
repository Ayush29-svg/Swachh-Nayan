import os
import re

# 1. Update studio_dashboard.html with Live Detection Banner and Simulation Button
with open("studio_dashboard.html", "r", encoding="utf-8") as f:
    html = f.read()

# Add detection banner over camera viewport if not present
banner_html = """                        <img id="liveCamImg" class="camera-img" src="/snapshot.bmp" alt="Luckfox Pico MIPI CSI Feed" onerror="onCameraImgError()" />

                        <!-- REAL-TIME AI DETECTION HUD BANNER -->
                        <div class="camera-detection-banner" id="cameraDetectionBanner" style="position: absolute; top: 48px; left: 14px; right: 14px; background: rgba(15, 23, 42, 0.88); backdrop-filter: blur(8px); border: 1.5px solid #38bdf8; border-radius: 8px; padding: 9px 15px; display: flex; align-items: center; justify-content: space-between; z-index: 10; box-shadow: 0 4px 20px rgba(0,0,0,0.6);">
                            <div style="display: flex; align-items: center; gap: 9px;">
                                <span class="pulse-dot" id="detectPulseDot" style="background: #10b981; box-shadow: 0 0 10px #10b981; width: 10px; height: 10px;"></span>
                                <span style="font-size: 0.85rem; font-weight: 800; color: #f8fafc; letter-spacing: 0.3px;" id="detectStatusText">CANAL CLEAR: SCANNING FOR FLOATING WASTE</span>
                            </div>
                            <div style="font-size: 0.75rem; color: #38bdf8; font-weight: 700; text-transform: uppercase;" id="detectConfText">YOLOv5n REAL-TIME NPU</div>
                        </div>"""

if '<div class="camera-detection-banner"' not in html:
    html = html.replace(
        '<img id="liveCamImg" class="camera-img" src="/snapshot.bmp" alt="Luckfox Pico MIPI CSI Feed" onerror="onCameraImgError()" />',
        banner_html,
        1
    )
    print("Added Real-Time AI Detection Banner to camera viewport!")

# Add Simulate Trash Detection button into Quick Bar
sim_btn = """<button onclick="simulateTrashDetection()" style="padding: 7px 16px; background: #ec4899; color: #ffffff; border: none; font-weight: 800; border-radius: 6px; cursor: pointer; font-size: 0.85rem; box-shadow: 0 2px 10px rgba(236, 72, 153, 0.4);">🎯 SIMULATE TRASH DETECT</button>"""
if 'simulateTrashDetection()' not in html:
    html = html.replace(
        '<button onclick="triggerTestSweep()"',
        sim_btn + '\n            <button onclick="triggerTestSweep()"'
    )
    print("Added Simulate Trash Detect button into top bar!")

# Add JS handler for simulateTrashDetection and updating detection banner in pollTelemetry
js_sim = """
        async function simulateTrashDetection() {
            showToast("Injecting simulated floating trash detection into YOLOv5n pipeline...", "warn");
            logEvent("AI", "Simulated floating trash event injected -> Gate diversion trigger queued.");
            try {
                const res = await fetch(BASE_URL + "/api/simulate_trash", { method: "POST" });
                if (res.ok) {
                    showToast("Trash detected! Servo gate actuating to divert trash!", "success");
                }
            } catch (err) {
                showToast("Simulate trigger error: " + err.message, "error");
            }
        }
"""
if 'function simulateTrashDetection' not in html:
    html = html.replace('function startTelemetryPolling() {', js_sim + '\n        function startTelemetryPolling() {')
    print("Added simulateTrashDetection JS function!")

# Update pollTelemetry to update camera detection banner
poll_patch = """
                // Update Live AI Detection Banner
                const detectBanner = document.getElementById("cameraDetectionBanner");
                const detectText = document.getElementById("detectStatusText");
                const detectDot = document.getElementById("detectPulseDot");
                const detectConf = document.getElementById("detectConfText");
                const targetLbl = d.target_label || "NONE";
                const targetConf = d.target_conf || 0.0;
                const gateState = d.gate_status || "NORMAL";

                if (gateState === "DIVERTING") {
                    detectText.innerText = `🚨 TRASH DETECTED: ${targetLbl.toUpperCase()} — ACTUATING GATE!`;
                    detectText.style.color = "#f43f5e";
                    detectDot.style.background = "#f43f5e";
                    detectDot.style.boxShadow = "0 0 12px #f43f5e";
                    detectBanner.style.borderColor = "#f43f5e";
                    detectConf.innerText = `CONF: ${targetConf.toFixed(1)}% | DIVERTING`;
                } else if (targetLbl !== "NONE" && targetConf > 10.0) {
                    detectText.innerText = `⚠️ TARGET ACQUIRED: ${targetLbl.toUpperCase()}`;
                    detectText.style.color = "#fbbf24";
                    detectDot.style.background = "#fbbf24";
                    detectDot.style.boxShadow = "0 0 10px #fbbf24";
                    detectBanner.style.borderColor = "#fbbf24";
                    detectConf.innerText = `CONF: ${targetConf.toFixed(1)}% | TRACKING`;
                } else {
                    detectText.innerText = "CANAL CLEAR: SCANNING FOR FLOATING WASTE";
                    detectText.style.color = "#f8fafc";
                    detectDot.style.background = "#10b981";
                    detectDot.style.boxShadow = "0 0 10px #10b981";
                    detectBanner.style.borderColor = "#38bdf8";
                    detectConf.innerText = "YOLOv5n REAL-TIME NPU";
                }
"""

if 'detectText.innerText =' not in html:
    html = html.replace(
        'document.getElementById("trashCountDisplay").innerText = d.trash_diverted || 0;',
        'document.getElementById("trashCountDisplay").innerText = d.trash_diverted || 0;\n' + poll_patch
    )
    print("Added dynamic telemetry banner update to pollTelemetry!")

with open("studio_dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Saved updated studio_dashboard.html!")
