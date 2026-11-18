import os

with open("studio_dashboard.html", "r", encoding="utf-8") as f:
    html_dashboard = f.read()

html_escaped = html_dashboard.replace('"""', r'\"\"\"')

server_template = '''#!/usr/bin/env python3
"""
Swachh-Nayan: Live Edge-Vision Production Master Server (Port 8088)
Integrates:
- Real-Time YOLOv5n AI Detection Tracking (from port 8080)
- Auto-Actuation of MG996R Servo Flap Gate on Trash Detection
- 16x2 Character I2C LCD Real-Time Display Sync
- SC3336 MIPI Camera Stream Proxy
- Studio UI Animated Dashboard
"""

from __future__ import annotations
import os
import sys
import time
import json
import urllib.request
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from hal.ads1115 import ADS1115
except Exception:
    ADS1115 = None

try:
    from hal.ultrasonic import UltrasonicSensor
except Exception:
    UltrasonicSensor = None

try:
    from hal.lcd1602 import LCD1602
except Exception:
    LCD1602 = None

PORT = 8088
PWM_CHIP = "/sys/class/pwm/pwmchip11"
PWM_NODE = "/sys/class/pwm/pwmchip11/pwm0"

RELAY_PINS = [54, 57, 59]
SERVO_GPIO_PINS = [48, 54, 56] # Multi-pin compatibility

LIVE_STATE = {
    "camera_fps": 10.0,
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
    "auto_divert": True, # ENABLED BY DEFAULT FOR IMMEDIATE AUTONOMOUS OPERATION
    "auto_cooldown_sec": 4.0,
    "pwm_active": True,
    "pwm_period_ns": 20000000,
    "pwm_freq_hz": 50.0,
    "pump_status": "OFF",
    "relay_polarity": "ACTIVE_HIGH",
    "water_voltage": 0.0,
    "water_percentage": 0.0,
    "ultrasonic_distance_cm": 0.0,
    "water_depth_cm": 0.0,
    "lcd_line1": "SWACHH-NAYAN  AI",
    "lcd_line2": "INITIALIZING...",
    "core_temp": "N/A",
    "rknpu_online": True,
    "camera_online": True,
    "camera_exposure": 800,
    "camera_gain": 2048,
    "camera_vflip": 1,
    "camera_hflip": 1,
    "last_update": time.time()
}

STATE_LOCK = threading.Lock()
SERVO_LOCK = threading.Lock()
RELAY_LOCK = threading.Lock()


def init_all_pins():
    """Initializes relay and servo candidate pins."""
    with RELAY_LOCK:
        for pin in RELAY_PINS + SERVO_GPIO_PINS:
            try:
                p_dir = f"/sys/class/gpio/gpio{pin}"
                if not os.path.exists(p_dir):
                    if os.path.exists("/sys/class/gpio/export"):
                        with open("/sys/class/gpio/export", "w") as f:
                            f.write(f"{pin}\\n")
                        time.sleep(0.01)
                with open(f"{p_dir}/direction", "w") as f:
                    f.write("out\\n")
            except Exception:
                pass


def init_hardware_pwm():
    """Initializes Rockchip Hardware PWM11 on Pin 4."""
    try:
        if os.path.exists("/sys/class/gpio/gpio55"):
            os.system("echo 55 > /sys/class/gpio/unexport 2>/dev/null")
            time.sleep(0.02)

        if not os.path.exists(PWM_NODE):
            if os.path.exists(f"{PWM_CHIP}/export"):
                with open(f"{PWM_CHIP}/export", "w") as f:
                    f.write("0\\n")
                time.sleep(0.05)

        if not os.path.exists(PWM_NODE):
            return False

        try:
            with open(f"{PWM_NODE}/period", "r") as f:
                cur_p = int(f.read().strip())
        except Exception:
            cur_p = 0

        if cur_p != 20000000:
            if os.path.exists(f"{PWM_NODE}/enable"):
                with open(f"{PWM_NODE}/enable", "w") as f:
                    f.write("0\\n")
            with open(f"{PWM_NODE}/period", "w") as f:
                f.write("20000000\\n")
            try:
                with open(f"{PWM_NODE}/polarity", "w") as f:
                    f.write("normal\\n")
            except Exception:
                pass
            with open(f"{PWM_NODE}/duty_cycle", "w") as f:
                f.write("1000000\\n")
            with open(f"{PWM_NODE}/enable", "w") as f:
                f.write("1\\n")

        return True
    except Exception as e:
        print(f"[PWM ERROR]: {e}")
        return False


def set_hardware_pump_relay(state_on: bool, invert_polarity: bool = False):
    init_all_pins()
    with RELAY_LOCK:
        val_str = "0\\n" if (state_on if invert_polarity else not state_on) else "1\\n"
        for pin in RELAY_PINS:
            try:
                val_path = f"/sys/class/gpio/gpio{pin}/value"
                with open(val_path, "w") as f:
                    f.write(val_str)
            except Exception:
                pass

        state_str = "ON" if state_on else "OFF"
        with STATE_LOCK:
            LIVE_STATE["pump_status"] = state_str
        print(f">> [RELAY] Motor set to {state_str}")
        return True


def actuate_servo_to_angle(angle_deg: float):
    """
    Drives MG996R servo via BOTH:
    1. Rockchip Hardware PWM11 on Pin 4
    2. Bit-banged pulses on candidate GPIOs
    """
    if os.path.exists("/sys/class/gpio/gpio55"):
        os.system("echo 55 > /sys/class/gpio/unexport 2>/dev/null")

    clamped_angle = max(0.0, min(180.0, float(angle_deg)))
    duty_ns = int(1000000 + (clamped_angle / 180.0) * 1000000)
    pulse_ms = duty_ns / 1000000.0

    # 1. Drive Hardware PWM11 (Pin 4)
    with SERVO_LOCK:
        init_hardware_pwm()
        try:
            with open(f"{PWM_NODE}/duty_cycle", "w") as f:
                f.write(f"{duty_ns}\\n")
            with open(f"{PWM_NODE}/enable", "w") as f:
                f.write("1\\n")
        except Exception:
            pass

        with STATE_LOCK:
            LIVE_STATE["servo_angle"] = round(clamped_angle, 1)
            LIVE_STATE["servo_pulse_ms"] = round(pulse_ms, 3)
            LIVE_STATE["servo_duty_ns"] = duty_ns
            LIVE_STATE["pwm_active"] = True

    # 2. ALSO Drive candidate GPIOs for 30 pulses
    pulse_high_s = duty_ns / 1e9

    def _pulse_gpios():
        try:
            open_fds = []
            for pin in SERVO_GPIO_PINS:
                p_val = f"/sys/class/gpio/gpio{pin}/value"
                if os.path.exists(p_val):
                    open_fds.append(open(p_val, "w"))

            for _ in range(35):
                for fd in open_fds:
                    fd.write("1\\n")
                    fd.flush()
                time.sleep(pulse_high_s)
                for fd in open_fds:
                    fd.write("0\\n")
                    fd.flush()
                time.sleep(max(0.001, 0.020 - pulse_high_s))

            for fd in open_fds:
                fd.close()
        except Exception:
            pass

    threading.Thread(target=_pulse_gpios, daemon=True).start()
    print(f">> [SERVO ACTUATION] Rotated Flap to {clamped_angle:.1f}° ({duty_ns} ns)")


def run_full_diversion_cycle(hold_seconds: float = 3.0):
    """Actuates flap to divert_angle, holds for duration, then returns to closed_angle."""
    with STATE_LOCK:
        if LIVE_STATE.get("gate_status") == "DIVERTING":
            return
        LIVE_STATE["gate_status"] = "DIVERTING"
        closed_ang = LIVE_STATE.get("closed_angle", 0.0)
        divert_ang = LIVE_STATE.get("divert_angle", 90.0)

    print(f">> [AI EVENT] Actuating gate to {divert_ang}° to divert detected trash...")
    actuate_servo_to_angle(divert_ang)
    time.sleep(hold_seconds)
    print(f">> [AI EVENT] Diversion complete. Returning gate to {closed_ang}° (normal flow)...")
    actuate_servo_to_angle(closed_ang)
    with STATE_LOCK:
        LIVE_STATE["gate_status"] = "NORMAL"


def background_hardware_worker():
    """Continuous hardware worker: polls YOLO stats from 8080, updates LCD, and triggers diversion."""
    print("[HARDWARE WORKER] Active: Synchronizing AI Vision, LCD, and Servo Actuation...")
    init_all_pins()
    init_hardware_pwm()

    adc = ADS1115(i2c_bus=3, address=0x48) if ADS1115 else None
    lcd = LCD1602(i2c_bus=3, address=0x27) if LCD1602 else None

    if lcd:
        try:
            lcd.clear()
            lcd.write_string("SWACHH-NAYAN  AI", 0)
            lcd.write_string("SYSTEM READY    ", 1)
        except Exception:
            pass

    screen_cycle = 0
    last_seen_trash_count = -1
    last_divert_trigger_time = 0.0

    while True:
        try:
            # 1. Read Water Level ADC
            v_water, pct_water = (0.0, 0.0)
            if adc:
                try:
                    v_water, pct_water = adc.read_water_level(channel=0)
                except Exception:
                    pass

            # 2. Read YOLOv5n Edge AI Detection Stats from port 8080
            fps = 10.0
            trash_count = 0
            t_label = "NONE"
            t_conf = 0.0
            app_gate = "NORMAL"

            try:
                req = urllib.request.Request("http://127.0.0.1:8080/api/stats", headers={"User-Agent": "SwachhBridge"})
                with urllib.request.urlopen(req, timeout=0.6) as resp:
                    npu_stats = json.loads(resp.read().decode("utf-8"))
                    fps = round(float(npu_stats.get("fps", 10.0)), 1)
                    trash_count = int(npu_stats.get("trash_count", 0))
                    t_label = str(npu_stats.get("target_label", "NONE"))
                    t_conf = float(npu_stats.get("target_conf", 0.0))
                    app_gate = str(npu_stats.get("gate_status", "NORMAL")).upper()

                    now = time.time()
                    with STATE_LOCK:
                        LIVE_STATE["camera_fps"] = fps
                        LIVE_STATE["trash_diverted"] = trash_count
                        LIVE_STATE["target_label"] = t_label
                        LIVE_STATE["target_conf"] = round(t_conf, 1)
                        LIVE_STATE["diverted_mass_kg"] = round(trash_count * 0.024, 3)
                        auto_enabled = LIVE_STATE.get("auto_divert", True)
                        cooldown = LIVE_STATE.get("auto_cooldown_sec", 4.0)

                    # Trigger Servo Diversion if trash detected
                    should_divert = (app_gate == "DIVERTING") or (last_seen_trash_count != -1 and trash_count > last_seen_trash_count)
                    if auto_enabled and should_divert and (now - last_divert_trigger_time) > cooldown:
                        last_divert_trigger_time = now
                        threading.Thread(target=run_full_diversion_cycle, args=(3.0,), daemon=True).start()

                    last_seen_trash_count = trash_count
            except Exception:
                pass

            # 3. Read Core SoC Temp
            core_temp = "N/A"
            try:
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as tf:
                    core_temp = f"{float(tf.read().strip()) / 1000.0:.1f}°C"
            except Exception:
                pass

            # 4. Synchronize 16x2 Character LCD Display with live AI detection info
            l1, l2 = "", ""
            if lcd:
                try:
                    current_gate = LIVE_STATE.get("gate_status", "NORMAL")
                    if current_gate == "DIVERTING" or app_gate == "DIVERTING":
                        # High-priority detection alert on physical LCD
                        lbl_short = t_label.split(" ")[0].upper()[:7]
                        l1 = f">> TRASH:{lbl_short} <<"[:16]
                        l2 = f"CONF:{t_conf:.0f}% CNT:{trash_count:2d}"[:16]
                    else:
                        if screen_cycle % 2 == 0:
                            l1 = "SWACHH-NAYAN  AI"[:16]
                            l2 = f"TRASH:{trash_count:2d} FPS:{fps:4.1f}"[:16]
                        else:
                            last_item = t_label.split(" ")[0][:8]
                            l1 = f"AI: {last_item} {t_conf:.0f}%"[:16]
                            l2 = f"GATE:OK W:{pct_water:3.0f}%"[:16]

                    lcd.write_string(l1.ljust(16), 0)
                    lcd.write_string(l2.ljust(16), 1)
                    screen_cycle += 1
                except Exception:
                    pass

            with STATE_LOCK:
                LIVE_STATE["water_voltage"] = round(v_water, 4)
                LIVE_STATE["water_percentage"] = round(pct_water, 1)
                LIVE_STATE["lcd_line1"] = l1
                LIVE_STATE["lcd_line2"] = l2
                LIVE_STATE["core_temp"] = core_temp
                LIVE_STATE["last_update"] = time.time()

        except Exception as e:
            print(f"[WORKER ERROR]: {e}")

        time.sleep(0.35)


HTML_DASHBOARD = r"""''' + html_escaped + '''"""


class LiveRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, User-Agent")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            body = HTML_DASHBOARD.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
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

        elif path == "/snapshot.bmp":
            try:
                req = urllib.request.Request("http://127.0.0.1:8080/snapshot.bmp")
                with urllib.request.urlopen(req, timeout=0.8) as resp:
                    bmp_bytes = resp.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/bmp")
                    self.send_header("Content-Length", str(len(bmp_bytes)))
                    self.send_header("Cache-Control", "no-cache")
                    self.send_cors_headers()
                    self.end_headers()
                    self.wfile.write(bmp_bytes)
            except Exception:
                self.send_error(503, "Camera stream unavailable")
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/set_motor":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                data = json.loads(body)
                target_state = str(data.get("state", "")).upper()
                if target_state in ["ON", "OFF"]:
                    set_hardware_pump_relay(target_state == "ON")
                current = LIVE_STATE.get("pump_status", "OFF")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "state": current}).encode("utf-8"))
            except Exception as e:
                self.send_error(400, f"Error: {e}")
            return

        elif path == "/api/set_servo_angle":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                data = json.loads(body)
                angle = float(data.get("angle", 0.0))
                actuate_servo_to_angle(angle)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "angle": LIVE_STATE.get("servo_angle"), "duty_ns": LIVE_STATE.get("servo_duty_ns")}).encode("utf-8"))
            except Exception as e:
                self.send_error(400, f"Error: {e}")
            return

        elif path == "/api/simulate_trash":
            try:
                # Trigger YOLO mock on 8080
                req = urllib.request.Request("http://127.0.0.1:8080/api/trigger_mock", data=b"", headers={"User-Agent": "SwachhBridge"})
                urllib.request.urlopen(req, timeout=1.0)
            except Exception:
                pass
            # Trigger full servo diversion cycle
            threading.Thread(target=run_full_diversion_cycle, args=(3.0,), daemon=True).start()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(b'{"status":"ok","event":"simulated_trash_divert"}')
            return

        elif path == "/api/test_servo_sweep":
            def _sweep():
                for ang in [0, 45, 90, 135, 180, 90, 0]:
                    actuate_servo_to_angle(ang)
                    time.sleep(0.8)
            threading.Thread(target=_sweep, daemon=True).start()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(b'{"status":"ok","sweep":"started"}')
            return

        elif path == "/api/toggle_auto_divert":
            with STATE_LOCK:
                LIVE_STATE["auto_divert"] = not LIVE_STATE.get("auto_divert", True)
                cur = LIVE_STATE["auto_divert"]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "auto_divert": cur}).encode("utf-8"))
            return

        elif path == "/api/reset_trash_counter":
            try:
                req = urllib.request.Request("http://127.0.0.1:8080/api/reset_counter", data=b"", headers={"User-Agent": "SwachhBridge"})
                urllib.request.urlopen(req, timeout=1.0)
            except Exception:
                pass
            with STATE_LOCK:
                LIVE_STATE["trash_diverted"] = 0
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(b'{"status":"ok","trash_diverted":0}')
            return

        self.send_error(404, "Not Found")


def main():
    print("=" * 65)
    print("  SWACHH-NAYAN: LIVE AI EDGE-VISION & SERVO ENGINE (PORT 8088)")
    print("=" * 65)
    t_worker = threading.Thread(target=background_hardware_worker, daemon=True, name="HwWorker")
    t_worker.start()

    server = ThreadingHTTPServer(("0.0.0.0", PORT), LiveRequestHandler)
    print(f">> Server listening on 0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
'''

with open("server_live_final.py", "w", encoding="utf-8") as f:
    f.write(server_template)

print("Generated complete production server_live_final.py!")
