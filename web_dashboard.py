"""
Swachh Nayan — Live Interactive Web Control Panel with Luckfox Pico CSI Camera Integration
Serves live Web Dashboard on http://localhost:8080.
Supports switching between Luckfox Pico MIPI CSI Camera Module (http://172.32.0.93:8080/video_feed) & Local Feed.
"""

import http.server
import socketserver
import json
import time
import threading
import os
import sys
import cv2
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config
from hardware_drivers.servo_driver import MG996RServoDriver
from hardware_drivers.lcd_driver import LCD1602I2CDriver
from hardware_drivers.ultrasonic_driver import HCSR04SensorDriver
from hardware_drivers.relay_driver import PumpRelayDriver
from ai_inference.opencv_detector import OpenCVWasteDetector

PORT = 8080

# System Global State
system_state = {
    "trash_count": 0,
    "servo_angle": 0,
    "servo_status": "RESTING (0° submerged)",
    "pump_status": "ON",
    "water_dist_cm": 12.5,
    "system_status": "SYSTEM ACTIVE",
    "last_detection": "None",
    "trigger_active": False,
    "pico_ip": "172.32.0.93"
}

servo = MG996RServoDriver()
lcd = LCD1602I2CDriver()
water_sensor = HCSR04SensorDriver()
pump = PumpRelayDriver()
pump.turn_on()
detector = OpenCVWasteDetector()

# Global Camera Stream & Animation Setup
cap = cv2.VideoCapture(config.CAMERA_INDEX)
has_real_cam = cap.isOpened()
if has_real_cam:
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    print(f"[CAM] Physical camera detected at index {config.CAMERA_INDEX}!")
else:
    print("[CAM] Physical camera not connected. Running synthetic HD AI stream generator.")

bottle_x = 60
bottle_y = 200

def trigger_scoop():
    global system_state, bottle_x
    if system_state["trigger_active"]:
        return
    system_state["trigger_active"] = True
    system_state["trash_count"] += 1
    system_state["servo_angle"] = 120
    system_state["servo_status"] = "DUMPING (120° over-rim)"
    system_state["system_status"] = "TRASH SCOOPING!"
    system_state["last_detection"] = time.strftime("%H:%M:%S")

    lcd.update_status(system_state["trash_count"], "TRASH SCOOPING!")
    servo.move_to_dump()
    time.sleep(config.SCOOP_HOLD_TIME_SEC)

    system_state["servo_angle"] = 0
    system_state["servo_status"] = "RESTING (0° submerged)"
    system_state["system_status"] = "SYSTEM ACTIVE"
    lcd.update_status(system_state["trash_count"], "SYSTEM ACTIVE")
    servo.move_to_rest()
    bottle_x = 60  # Reset bottle to inlet start
    system_state["trigger_active"] = False

def generate_video_frame():
    """Captures real camera frame or generates simulated water channel stream."""
    global bottle_x, bottle_y

    if has_real_cam:
        ret, frame = cap.read()
        if ret:
            annotated_frame, detections = detector.detect_waste(frame)
            return annotated_frame

    # Synthetic Water Channel Animation Generator
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Water background (Blue gradient with animated flow lines)
    frame[:, :] = (80, 45, 15)  # Dark water blue
    t = time.time()
    
    # Draw water flow lines
    for i in range(5):
        y_pos = int((100 + i * 70 + t * 40) % 480)
        cv2.line(frame, (0, y_pos), (640, y_pos + 20), (120, 75, 30), 1)

    # Animate bottle moving downstream toward trigger zone if pump is ON
    if pump.is_pump_on and not system_state["trigger_active"]:
        bottle_x += 3
        if bottle_x > 580:
            bottle_x = 60

    # Draw floating plastic bottle in channel
    cv2.rectangle(frame, (int(bottle_x), bottle_y), (int(bottle_x) + 70, bottle_y + 110), (240, 240, 240), -1)
    cv2.rectangle(frame, (int(bottle_x) + 20, bottle_y - 20), (int(bottle_x) + 50, bottle_y), (0, 0, 200), -1)
    cv2.putText(frame, "PLASTIC BOTTLE", (int(bottle_x) - 10, bottle_y + 130),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    # Run Waste Detector (computes bounding boxes & trigger zone overlay)
    annotated_frame, detections = detector.detect_waste(frame)

    # Check if bottle entered trigger zone automatically
    for det in detections:
        if det["in_trigger_zone"] and not system_state["trigger_active"]:
            threading.Thread(target=trigger_scoop, daemon=True).start()

    return annotated_frame


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Swachh Nayan — Live AI Control Panel & Camera Stream</title>
    <style>
        :root {
            --bg-color: #0d1117;
            --panel-bg: #161b22;
            --border-color: #30363d;
            --accent-cyan: #58a6ff;
            --accent-green: #3fb950;
            --accent-red: #f85149;
            --accent-yellow: #d29922;
            --text-main: #c9d1d9;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 20px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 15px;
            margin-bottom: 20px;
        }
        .header h1 {
            margin: 0;
            color: var(--accent-cyan);
            font-size: 24px;
        }
        .badge {
            background: rgba(63, 185, 80, 0.2);
            color: var(--accent-green);
            border: 1px solid var(--accent-green);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: bold;
        }
        /* IP Bar */
        .ip-bar {
            background: #161b22;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px 20px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap;
        }
        .ip-bar label {
            font-weight: bold;
            font-size: 14px;
            color: var(--accent-cyan);
        }
        .ip-input {
            background: #0d1117;
            border: 1px solid var(--border-color);
            color: #fff;
            padding: 8px 12px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 14px;
            width: 200px;
        }
        .ip-btn {
            background: #238636;
            color: #fff;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: bold;
            cursor: pointer;
        }
        .ip-btn:hover { background: #2ea043; }
        .ip-btn-blue {
            background: #1f6feb;
        }
        .ip-btn-blue:hover { background: #388bfd; }
        
        .grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
        }
        .card {
            background: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 20px;
        }
        .card-title {
            font-size: 16px;
            font-weight: bold;
            color: var(--accent-cyan);
            margin-bottom: 15px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 8px;
        }
        /* Video Stream Container */
        .video-box {
            position: relative;
            width: 100%;
            height: 380px;
            background: #000;
            border-radius: 6px;
            overflow: hidden;
            border: 1px solid #30363d;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .video-box img {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        .video-overlay {
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0,0,0,0.8);
            padding: 6px 12px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            color: var(--accent-green);
            z-index: 10;
        }
        /* Metrics Gauges */
        .stat-group {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: #0d1117;
            border: 1px solid var(--border-color);
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }
        .stat-value {
            font-size: 28px;
            font-weight: bold;
            color: var(--accent-green);
            margin: 8px 0 4px 0;
        }
        .stat-label {
            font-size: 12px;
            color: #8b949e;
            text-transform: uppercase;
        }
        /* LCD Screen Simulation */
        .lcd-screen {
            background: #205c20;
            color: #98ff98;
            font-family: "Courier New", Courier, monospace;
            padding: 15px;
            border-radius: 6px;
            border: 3px solid #103010;
            box-shadow: inset 0 0 10px #000;
            font-size: 16px;
            font-weight: bold;
            letter-spacing: 2px;
            line-height: 1.5;
            margin-bottom: 20px;
        }
        /* Control Buttons */
        .btn-group {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .btn {
            background: #238636;
            color: #fff;
            border: none;
            padding: 12px 18px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.2s ease;
        }
        .btn:hover { background: #2ea043; }
        .btn-red { background: #da3633; }
        .btn-red:hover { background: #f85149; }
        .btn-blue { background: #1f6feb; }
        .btn-blue:hover { background: #388bfd; }
    </style>
</head>
<body>

    <div class="header">
        <div>
            <h1>SWACHH NAYAN — Live AI Control Panel</h1>
            <small style="color: #8b949e;">Waveshare Luckfox Pico (RV1103 NPU) | Real-time Hardware Integration</small>
        </div>
        <div class="badge" id="statusBadge">● SYSTEM ONLINE</div>
    </div>

    <!-- Luckfox Pico IP & Source Selector -->
    <div class="ip-bar">
        <label for="picoIp">Luckfox Pico Board IP:</label>
        <input type="text" id="picoIp" class="ip-input" value="172.32.0.93" placeholder="172.32.0.93">
        <button class="ip-btn" onclick="switchSource('pico')">CONNECT PICO MIPI CSI CAMERA</button>
        <button class="ip-btn ip-btn-blue" onclick="switchSource('local')">LOCAL STREAM FEED</button>
        <span style="font-size: 12px; color: #8b949e;">Default USB RNDIS IP: <b>172.32.0.93</b></span>
    </div>

    <div class="grid">
        <!-- Left: Live Video Stream -->
        <div class="card">
            <div class="card-title">LIVE CAMERA FEED STREAM</div>
            <div class="video-box">
                <div class="video-overlay" id="streamOverlay">● STREAM SOURCE: /video_feed</div>
                <img id="streamImg" src="/video_feed" alt="Live Camera Stream" onerror="handleStreamError();" />
            </div>
            <p style="font-size: 12px; color: #8b949e; margin-top: 12px;">
                * Direct stream with cyan <b>Scoop Trigger Zone</b>. When floating plastic enters the box, the MG996R servo triggers automatically.
            </p>
        </div>

        <!-- Right: Telemetry & Controls -->
        <div class="card">
            <div class="card-title">SYSTEM TELEMETRY & METRICS</div>
            
            <div class="stat-group">
                <div class="stat-card">
                    <div class="stat-label">Total Trash Collected</div>
                    <div class="stat-value" id="trashCount">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Water Distance</div>
                    <div class="stat-value" id="waterDist" style="color: var(--accent-cyan);">12.5 cm</div>
                </div>
            </div>

            <div class="card-title">16x2 I2C LCD SCREEN FEED</div>
            <div class="lcd-screen" id="lcdFeed">
                TRASH CT: 0000<br>
                SYSTEM ACTIVE
            </div>

            <div class="card-title">HARDWARE CONTROLS</div>
            <div class="btn-group">
                <button class="btn btn-blue" onclick="triggerScoopCycle()">TRIGGER OVERHEAD SCOOP CYCLE</button>
                <button class="btn" onclick="togglePump()">TOGGLE 12V PUMP RELAY (ON/OFF)</button>
                <button class="btn btn-red" onclick="resetBottle()">RESET FLOATING BOTTLE</button>
            </div>
        </div>
    </div>

    <script>
        function switchSource(source) {
            const img = document.getElementById('streamImg');
            const overlay = document.getElementById('streamOverlay');
            const badge = document.getElementById('statusBadge');

            if (source === 'pico') {
                let ip = document.getElementById('picoIp').value.trim() || "172.32.0.93";
                let picoUrl = "http://" + ip + ":8080/video_feed";
                img.src = picoUrl;
                overlay.innerText = "● PICO MIPI CSI STREAM: " + picoUrl;
                badge.innerText = "● CONNECTING PICO CAM...";
            } else {
                img.src = "/video_feed";
                overlay.innerText = "● STREAM SOURCE: /video_feed";
                badge.innerText = "● LOCAL STREAM ACTIVE";
                badge.style.borderColor = "#3fb950";
                badge.style.color = "#3fb950";
            }
        }

        function handleStreamError() {
            const badge = document.getElementById('statusBadge');
            badge.innerText = "● PICO CAM OFFLINE (FALLBACK TO LOCAL)";
            badge.style.borderColor = "#d29922";
            badge.style.color = "#d29922";
            document.getElementById('streamImg').src = "/video_feed";
        }

        function updateTelemetry() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('trashCount').innerText = data.trash_count;
                    document.getElementById('waterDist').innerText = data.water_dist_cm + " cm";
                    document.getElementById('lcdFeed').innerHTML = 
                        "TRASH CT: " + String(data.trash_count).padStart(4, '0') + "<br>" + data.system_status;
                }).catch(e => console.log('Offline mode'));
        }

        function triggerScoopCycle() {
            fetch('/api/trigger_scoop', {method: 'POST'}).then(() => updateTelemetry());
        }

        function togglePump() {
            fetch('/api/toggle_pump', {method: 'POST'}).then(() => updateTelemetry());
        }

        function resetBottle() {
            fetch('/api/reset_bottle', {method: 'POST'}).then(() => updateTelemetry());
        }

        setInterval(updateTelemetry, 1000);
    </script>
</body>
</html>
"""

class SwachhNayanHTTPHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))

        elif self.path == "/video_feed":
            self.send_response(200)
            self.send_header("Content-type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()

            try:
                while True:
                    frame = generate_video_frame()
                    ret, jpeg = cv2.imencode('.jpg', frame)
                    if not ret:
                        continue
                    
                    self.wfile.write(b'--frame\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', str(len(jpeg)))
                    self.end_headers()
                    self.wfile.write(jpeg.tobytes())
                    self.wfile.write(b'\r\n')
                    time.sleep(0.04)  # ~25 FPS
            except Exception:
                pass

        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(system_state).encode("utf-8"))
        else:
            self.send_error(404)

    def do_POST(self):
        global system_state, bottle_x
        if self.path == "/api/trigger_scoop":
            threading.Thread(target=trigger_scoop, daemon=True).start()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')

        elif self.path == "/api/toggle_pump":
            new_state = not pump.is_pump_on
            pump.set_pump(new_state)
            system_state["pump_status"] = "ON" if new_state else "OFF"
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')

        elif self.path == "/api/reset_bottle":
            bottle_x = 60
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        else:
            self.send_error(404)


class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Serve the long-lived MJPEG stream without blocking dashboard APIs."""
    allow_reuse_address = True
    daemon_threads = True


def start_server():
    server = ThreadingHTTPServer(("", PORT), SwachhNayanHTTPHandler)
    print("==========================================================")
    print(f" SWACHH NAYAN LIVE CONTROL PANEL ONLINE AT:")
    print(f" http://localhost:{PORT}")
    print("==========================================================")
    server.serve_forever()

if __name__ == "__main__":
    start_server()
