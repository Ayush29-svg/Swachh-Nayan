#!/usr/bin/env python3
"""
SWACHH NAYAN — Master Laptop Live Feed & Control Studio
Communicates with ESP32-S3-CAM on COM5 (Serial) and hosts the Live Studio Dashboard on Port 8088.
"""

from __future__ import annotations
import os
import sys
import time
import json
import threading
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import io
import math

# Optional dependencies
try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

PORT = 8088
DEFAULT_COM_PORT = "COM5"
BAUD_RATE = 115200

# Global Live Telemetry State
LIVE_STATE = {
    "camera_fps": 15.0,
    "trash_diverted": 0,
    "target_label": "NONE",
    "target_conf": 0.0,
    "diverted_mass_kg": 0.0,
    "gate_status": "NORMAL",
    "servo_angle": 0.0,
    "closed_angle": 0.0,
    "divert_angle": 90.0,
    "servo_pulse_ms": 1.0,
    "servo_duty_ns": 1000000,
    "auto_divert": True,
    "auto_cooldown_sec": 4.0,
    "pwm_active": True,
    "pwm_period_ns": 20000000,
    "pwm_freq_hz": 50.0,
    "pump_status": "OFF",
    "relay_polarity": "ACTIVE_HIGH",
    "water_voltage": 1.85,
    "water_percentage": 24.5,
    "ultrasonic_distance_cm": 22.8,
    "water_depth_cm": 7.2,
    "lcd_line1": "SWACHH-NAYAN S3",
    "lcd_line2": "MONITOR ONLINE",
    "core_temp": "42°C",
    "rknpu_online": True,
    "camera_online": True,
    "camera_exposure": 800,
    "camera_gain": 2048,
    "camera_vflip": 0,
    "camera_hflip": 0,
    "serial_connected": False,
    "serial_port": DEFAULT_COM_PORT,
    "last_update": time.time(),
}

STATE_LOCK = threading.Lock()
SERIAL_LOCK = threading.Lock()
SERIAL_OBJ = None

# Load Studio HTML
DASHBOARD_FILE = os.path.join(os.path.dirname(__file__), "studio_dashboard.html")
if os.path.exists(DASHBOARD_FILE):
    with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
        HTML_DASHBOARD = f.read()
else:
    HTML_DASHBOARD = "<h1>Swachh Nayan Studio UI missing</h1>"


def send_serial_command(cmd_str: str) -> bool:
    """Send text command line to ESP32 over serial."""
    global SERIAL_OBJ
    with SERIAL_LOCK:
        if SERIAL_OBJ and SERIAL_OBJ.is_open:
            try:
                line = (cmd_str.strip() + "\n").encode("utf-8")
                SERIAL_OBJ.write(line)
                SERIAL_OBJ.flush()
                print(f"[SERIAL TX -> ESP32] {cmd_str}")
                return True
            except Exception as e:
                print(f"[SERIAL TX Error] {e}")
                SERIAL_OBJ = None
    return False


def serial_worker():
    """Background worker that continuously reads live sensor feed from ESP32."""
    global SERIAL_OBJ
    print(f"[SERIAL] Worker started. Target port: {DEFAULT_COM_PORT} @ {BAUD_RATE}")

    while True:
        try:
            if SERIAL_OBJ is None or not SERIAL_OBJ.is_open:
                # Find available ports
                available = [p.device for p in serial.tools.list_ports.comports()] if serial else []
                target_port = DEFAULT_COM_PORT if DEFAULT_COM_PORT in available else (available[0] if available else None)

                if target_port and serial:
                    try:
                        print(f"[SERIAL] Attempting connection to {target_port}...")
                        s = serial.Serial(target_port, BAUD_RATE, timeout=1.0)
                        with SERIAL_LOCK:
                            SERIAL_OBJ = s
                        with STATE_LOCK:
                            LIVE_STATE["serial_connected"] = True
                            LIVE_STATE["serial_port"] = target_port
                        print(f"[SERIAL] Successfully connected to {target_port}!")
                    except Exception as e:
                        time.sleep(2.0)
                        continue
                else:
                    with STATE_LOCK:
                        LIVE_STATE["serial_connected"] = False
                    time.sleep(2.0)
                    continue

            # Read serial lines
            line_bytes = SERIAL_OBJ.readline()
            if not line_bytes:
                continue

            line = line_bytes.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            # Check for JSON telemetry packet
            if line.startswith("TELEMETRY:"):
                raw_json = line[len("TELEMETRY:"):].strip()
                try:
                    data = json.loads(raw_json)
                    with STATE_LOCK:
                        if "ultrasonic_distance_cm" in data:
                            LIVE_STATE["ultrasonic_distance_cm"] = round(float(data["ultrasonic_distance_cm"]), 1)
                        if "water_depth_cm" in data:
                            LIVE_STATE["water_depth_cm"] = round(float(data["water_depth_cm"]), 1)
                        if "water_percentage" in data:
                            LIVE_STATE["water_percentage"] = round(float(data["water_percentage"]), 1)
                        if "pump_status" in data:
                            LIVE_STATE["pump_status"] = str(data["pump_status"]).upper()
                        if "gate_status" in data:
                            LIVE_STATE["gate_status"] = str(data["gate_status"]).upper()
                        if "servo_angle" in data:
                            LIVE_STATE["servo_angle"] = round(float(data["servo_angle"]), 1)
                        if "trash_diverted" in data:
                            LIVE_STATE["trash_diverted"] = int(data["trash_diverted"])
                        if "camera_online" in data:
                            LIVE_STATE["camera_online"] = bool(data["camera_online"])
                        LIVE_STATE["last_update"] = time.time()
                except Exception:
                    pass
            elif "[CAMERA] Sensor PID:" in line:
                with STATE_LOCK:
                    LIVE_STATE["camera_online"] = True
            elif "[HEARTBEAT]" in line:
                with STATE_LOCK:
                    LIVE_STATE["last_update"] = time.time()

        except Exception as e:
            print(f"[SERIAL Exception] {e}")
            with SERIAL_LOCK:
                if SERIAL_OBJ:
                    try:
                        SERIAL_OBJ.close()
                    except Exception:
                        pass
                    SERIAL_OBJ = None
            with STATE_LOCK:
                LIVE_STATE["serial_connected"] = False
            time.sleep(2.0)


def generate_live_synthetic_frame() -> bytes:
    """Renders a dynamic live camera diagnostic image showing flow, sensors, and detections."""
    width, height = 640, 480
    if cv2 is not None and np is not None:
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Flowing water simulation
        t = time.time()
        for y in range(height):
            # Gradient blue background for water drain
            b = int(45 + 30 * math.sin(y * 0.02 + t * 3))
            g = int(30 + 20 * math.sin(y * 0.01 + t * 2))
            r = 15
            frame[y, :] = (b, g, r)

        # Water channel bounds
        cv2.line(frame, (100, 0), (100, height), (0, 200, 255), 2)
        cv2.line(frame, (540, 0), (540, height), (0, 200, 255), 2)

        # Trigger Zone Box
        tz_x1, tz_y1 = int(0.2 * width), int(0.3 * height)
        tz_x2, tz_y2 = int(0.8 * width), int(0.7 * height)
        cv2.rectangle(frame, (tz_x1, tz_y1), (tz_x2, tz_y2), (0, 255, 0), 2)
        cv2.putText(frame, "AI TRIGGER ZONE", (tz_x1 + 8, tz_y1 + 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Floating waste item moving along stream
        phase = (t * 0.6) % 1.0
        waste_y = int(50 + phase * 380)
        waste_x = int(320 + 40 * math.sin(phase * 6.28))
        
        with STATE_LOCK:
            servo_ang = LIVE_STATE["servo_angle"]
            pump_on = (LIVE_STATE["pump_status"] == "ON")
            dist = LIVE_STATE["ultrasonic_distance_cm"]
            depth = LIVE_STATE["water_depth_cm"]
            trash_num = LIVE_STATE["trash_diverted"]

        # Draw detected plastic bottle
        cv2.rectangle(frame, (waste_x - 30, waste_y - 20), (waste_x + 30, waste_y + 20), (0, 165, 255), 2)
        cv2.putText(frame, "plastic_bottle: 0.94", (waste_x - 45, waste_y - 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)

        # Telemetry HUD on video
        cv2.putText(frame, f"SWACHH-NAYAN S3 | OV3660 FEED", (16, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"DISTANCE: {dist:.1f} cm | DEPTH: {depth:.1f} cm", (16, 62),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (56, 189, 248), 2)
        cv2.putText(frame, f"PUMP: {'RUNNING' if pump_on else 'OFF'} | FLAP: {servo_ang:.0f} deg | DIVERTED: {trash_num}", 
                    (16, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (16, 185, 129) if pump_on else (200, 200, 200), 2)

        # Gate Flap Graphic
        gate_x = 520
        gate_y = 350
        rad = math.radians(servo_ang)
        end_x = int(gate_x - 80 * math.cos(rad))
        end_y = int(gate_y - 80 * math.sin(rad))
        cv2.line(frame, (gate_x, gate_y), (end_x, end_y), (255, 50, 50), 6)
        cv2.putText(frame, f"FLAP [{servo_ang:.0f} deg]", (gate_x - 90, gate_y + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 100), 2)

        ret, buffer = cv2.imencode(".bmp", frame)
        if ret:
            return buffer.tobytes()

    # Fallback minimal 1x1 BMP
    return b'BM\x36\x00\x00\x00\x00\x00\x00\x00\x36\x00\x00\x00\x28\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'


class StudioHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence routine telemetry polling logs
        return

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ["/", "/index.html"]:
            body = HTML_DASHBOARD.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(body)
            return

        elif path == "/api/live_telemetry":
            with STATE_LOCK:
                data = json.dumps(LIVE_STATE).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(data)
            return

        elif path in ["/snapshot.bmp", "/snapshot.jpg"]:
            frame_bytes = generate_live_synthetic_frame()
            self.send_response(200)
            self.send_header("Content-Type", "image/bmp")
            self.send_header("Content-Length", str(len(frame_bytes)))
            self.send_header("Cache-Control", "no-cache")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(frame_bytes)
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            req_data = json.loads(body)
        except Exception:
            req_data = {}

        if path == "/api/set_motor":
            target = str(req_data.get("state", "OFF")).upper()
            send_serial_command(f"CMD:PUMP:{'ON' if target == 'ON' else 'OFF'}")
            with STATE_LOCK:
                LIVE_STATE["pump_status"] = target
            self.send_json_response({"status": "ok", "state": target})
            return

        elif path == "/api/set_servo_angle":
            angle = float(req_data.get("angle", 0.0))
            send_serial_command(f"CMD:SERVO:{angle:.1f}")
            with STATE_LOCK:
                LIVE_STATE["servo_angle"] = angle
                LIVE_STATE["gate_status"] = "DIVERTING" if angle > 30 else "NORMAL"
            self.send_json_response({"status": "ok", "angle": angle})
            return

        elif path in ["/api/test_servo_sweep", "/api/trigger_diversion"]:
            send_serial_command("CMD:DIVERT")
            with STATE_LOCK:
                LIVE_STATE["gate_status"] = "DIVERTING"
                LIVE_STATE["servo_angle"] = 90.0
                LIVE_STATE["trash_diverted"] += 1
            
            def _reset_gate():
                time.sleep(2.5)
                with STATE_LOCK:
                    LIVE_STATE["gate_status"] = "NORMAL"
                    LIVE_STATE["servo_angle"] = 0.0

            threading.Thread(target=_reset_gate, daemon=True).start()
            self.send_json_response({"status": "ok", "message": "Diversion triggered"})
            return

        elif path == "/api/toggle_auto_divert":
            with STATE_LOCK:
                LIVE_STATE["auto_divert"] = not LIVE_STATE["auto_divert"]
                val = LIVE_STATE["auto_divert"]
            self.send_json_response({"status": "ok", "auto_divert": val})
            return

        elif path == "/api/reset_trash_counter":
            send_serial_command("CMD:RESET_COUNT")
            with STATE_LOCK:
                LIVE_STATE["trash_diverted"] = 0
            self.send_json_response({"status": "ok", "trash_diverted": 0})
            return

        elif path == "/api/simulate_trash":
            with STATE_LOCK:
                LIVE_STATE["target_label"] = "plastic_bottle"
                LIVE_STATE["target_conf"] = 0.94
                LIVE_STATE["trash_diverted"] += 1
                LIVE_STATE["gate_status"] = "DIVERTING"
                LIVE_STATE["servo_angle"] = 90.0
            send_serial_command("CMD:DIVERT")

            def _cooldown():
                time.sleep(2.5)
                with STATE_LOCK:
                    LIVE_STATE["gate_status"] = "NORMAL"
                    LIVE_STATE["servo_angle"] = 0.0
                    LIVE_STATE["target_label"] = "NONE"
                    LIVE_STATE["target_conf"] = 0.0

            threading.Thread(target=_cooldown, daemon=True).start()
            self.send_json_response({"status": "ok", "detected": True})
            return

        elif path == "/api/force_close":
            send_serial_command("CMD:SERVO:0.0")
            with STATE_LOCK:
                LIVE_STATE["gate_status"] = "NORMAL"
                LIVE_STATE["servo_angle"] = 0.0
            self.send_json_response({"status": "ok"})
            return

        self.send_error(404, "Not Found")

    def send_json_response(self, obj: dict):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(data)


def main():
    print("=" * 60)
    print("   SWACHH-NAYAN: LIVE EDGE AI STUDIO & SENSOR DASHBOARD   ")
    print(f"   Connecting to ESP32-S3 on {DEFAULT_COM_PORT} @ {BAUD_RATE} baud   ")
    print(f"   Hosting Studio UI on http://localhost:{PORT}            ")
    print("=" * 60)

    # 1. Start Serial Background Thread
    serial_th = threading.Thread(target=serial_worker, daemon=True)
    serial_th.start()

    # 2. Start HTTP Server
    server = ThreadingHTTPServer(("0.0.0.0", PORT), StudioHTTPHandler)
    server_th = threading.Thread(target=server.serve_forever, daemon=True)
    server_th.start()
    print(f">> Studio Server listening on http://127.0.0.1:{PORT}")
    print(f">> Opening dashboard in your browser...")

    try:
        webbrowser.open(f"http://127.0.0.1:{PORT}")
    except Exception:
        pass

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Stopping Swachh Nayan Studio Server...")
        server.shutdown()


if __name__ == "__main__":
    main()
