import os

with open("studio_dashboard.html", "r", encoding="utf-8") as f:
    html_content = f.read()

html_escaped = html_content.replace('"""', r'\"\"\"')

server_code = '''#!/usr/bin/env python3
"""
Swachh-Nayan: Live Production Master Telemetry & Universal Multi-Pin Hardware Engine
Supports all hardware revisions & pinout variants on Waveshare Luckfox Pico RV1103:
- Servo: Pin 4 (Hardware PWM11) AND Pin 35 (GPIO56) simultaneously
- Relay: Pin 5 (GPIO54), Pin 36 (GPIO57), and Pin 38 (GPIO59) simultaneously
- Relay Polarity: Auto-toggles and supports both Active-High and Active-Low optocouplers
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

# Multi-Pin Relay Targets (Pin 5, Pin 36, Pin 38)
RELAY_PINS = [54, 57, 59]
SERVO_GPIO_PIN = 56 # Pin 35

LIVE_STATE = {
    "camera_fps": 0.0,
    "trash_diverted": 0,
    "gate_status": "NORMAL",
    "servo_angle": 0.0,
    "closed_angle": 0.0,
    "divert_angle": 90.0,
    "servo_pulse_ms": 1.0,
    "servo_duty_ns": 1000000,
    "auto_divert": False,
    "auto_cooldown_sec": 8.0,
    "pwm_active": True,
    "pwm_period_ns": 20000000,
    "pwm_freq_hz": 50.0,
    "pump_status": "OFF",
    "relay_polarity": "ACTIVE_HIGH",
    "water_voltage": 0.0,
    "water_percentage": 0.0,
    "ultrasonic_distance_cm": 0.0,
    "water_depth_cm": 0.0,
    "lcd_line1": "SWACHH-NAYAN",
    "lcd_line2": "INITIALIZING",
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


def init_all_relay_pins():
    """Initializes all candidate relay GPIO pins as outputs."""
    with RELAY_LOCK:
        for pin in RELAY_PINS:
            try:
                p_dir = f"/sys/class/gpio/gpio{pin}"
                if not os.path.exists(p_dir):
                    if os.path.exists("/sys/class/gpio/export"):
                        with open("/sys/class/gpio/export", "w") as f:
                            f.write(f"{pin}\\n")
                        time.sleep(0.02)
                with open(f"{p_dir}/direction", "w") as f:
                    f.write("out\\n")
            except Exception:
                pass


def set_hardware_pump_relay(state_on: bool, invert_polarity: bool = False):
    """
    Drives ALL candidate relay pins (GPIO 54, GPIO 57, GPIO 59) simultaneously.
    Supports both Active-High and Active-Low relay trigger circuits.
    """
    init_all_relay_pins()
    with RELAY_LOCK:
        if invert_polarity:
            val_str = "0\\n" if state_on else "1\\n"
        else:
            val_str = "1\\n" if state_on else "0\\n"

        for pin in RELAY_PINS:
            try:
                val_path = f"/sys/class/gpio/gpio{pin}/value"
                with open(val_path, "w") as f:
                    f.write(val_str)
            except Exception as e:
                print(f"[RELAY ERROR] Failed writing {val_str.strip()} to GPIO{pin}: {e}")

        state_str = "ON" if state_on else "OFF"
        with STATE_LOCK:
            LIVE_STATE["pump_status"] = state_str
        print(f">> [RELAY MULTI-DRIVE] Set GPIOs {RELAY_PINS} -> {val_str.strip()} (Motor {state_str})")
        return True


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


def actuate_servo_to_angle(angle_deg: float):
    """
    Drives MG996R servo via BOTH:
    1. Rockchip Hardware PWM11 on Pin 4 (GPIO1_C7 / Pin 55)
    2. Software Bit-Banged PWM on Pin 35 (GPIO1_C0 / Pin 56 - as per Assembly Guide)
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

    # 2. ALSO Drive Pin 35 (GPIO56)
    pulse_high_s = duty_ns / 1e9

    def _pulse_pin35():
        try:
            p_dir = f"/sys/class/gpio/gpio{SERVO_GPIO_PIN}"
            if not os.path.exists(p_dir):
                if os.path.exists("/sys/class/gpio/export"):
                    with open("/sys/class/gpio/export", "w") as f:
                        f.write(f"{SERVO_GPIO_PIN}\\n")
                    time.sleep(0.02)
            with open(f"{p_dir}/direction", "w") as f:
                f.write("out\\n")

            with open(f"{p_dir}/value", "w") as f:
                for _ in range(50):
                    f.write("1\\n")
                    f.flush()
                    time.sleep(pulse_high_s)
                    f.write("0\\n")
                    f.flush()
                    time.sleep(max(0.001, 0.020 - pulse_high_s))
        except Exception:
            pass

    threading.Thread(target=_pulse_pin35, daemon=True).start()
    print(f">> [SERVO DUAL-DRIVE] Actuated Pin 4 & Pin 35 to {clamped_angle:.1f}° ({duty_ns} ns)")


def run_full_diversion_cycle(hold_seconds: float = 2.5):
    """Actuates flap to divert_angle, holds for duration, then returns to closed_angle."""
    with STATE_LOCK:
        if LIVE_STATE.get("gate_status") == "DIVERTING":
            return
        LIVE_STATE["gate_status"] = "DIVERTING"
        closed_ang = LIVE_STATE.get("closed_angle", 0.0)
        divert_ang = LIVE_STATE.get("divert_angle", 90.0)

    print(f">> [SERVO CYCLE] Moving flap from {closed_ang}° to {divert_ang}° DIVERT...")
    actuate_servo_to_angle(divert_ang)
    time.sleep(hold_seconds)
    print(f">> [SERVO CYCLE] Returning flap to {closed_ang}° CLOSED...")
    actuate_servo_to_angle(closed_ang)
    with STATE_LOCK:
        LIVE_STATE["gate_status"] = "CLOSED"


def set_hardware_camera_controls(exposure: int = None, gain: int = None, vflip: int = None, hflip: int = None):
    """Programs SC3336 sensor registers directly via v4l2-ctl on /dev/v4l-subdev2."""
    cmd_parts = []
    if exposure is not None:
        cmd_parts.append(f"--set-ctrl=exposure={max(1, min(1350, int(exposure)))}")
    if gain is not None:
        cmd_parts.append(f"--set-ctrl=analogue_gain={max(128, min(8192, int(gain)))}")
    if vflip is not None:
        cmd_parts.append(f"--set-ctrl=vertical_flip={1 if vflip else 0}")
    if hflip is not None:
        cmd_parts.append(f"--set-ctrl=horizontal_flip={1 if hflip else 0}")

    if cmd_parts:
        cmd = f"v4l2-ctl -d /dev/v4l-subdev2 {' '.join(cmd_parts)} 2>/dev/null"
        os.system(cmd)


def background_hardware_worker():
    """Continuous hardware worker polling sensors, registers, and syncing LCD."""
    print("[HARDWARE WORKER] Initializing Multi-Pin Engine & Sensors...")
    init_all_relay_pins()
    init_hardware_pwm()
    set_hardware_camera_controls(exposure=800, gain=2048, vflip=1, hflip=1)

    adc = ADS1115(i2c_bus=3, address=0x48) if ADS1115 else None
    ultra = UltrasonicSensor(trig_pin=53, echo_pin=52, channel_depth_cm=22.0) if UltrasonicSensor else None
    lcd = LCD1602(i2c_bus=3, address=0x27) if LCD1602 else None

    if lcd:
        try:
            lcd.clear()
            lcd.write_string("SWACHH-NAYAN".center(16), 0)
            lcd.write_string("LIVE DASHBOARD".center(16), 1)
        except Exception:
            pass

    screen_cycle = 0
    last_seen_trash_count = -1
    last_divert_trigger_time = 0.0

    while True:
        try:
            v_water, pct_water = (0.0, 0.0)
            if adc:
                try:
                    v_water, pct_water = adc.read_water_level(channel=0)
                except Exception:
                    pass

            dist_ultra = 0.0
            depth_cm = 0.0
            if ultra:
                try:
                    raw_d = ultra.measure_raw_distance_cm()
                    if raw_d is not None:
                        dist_ultra = raw_d
                        depth_cm = round(max(0.0, 22.0 - raw_d), 1)
                except Exception:
                    pass

            fps = 0.0
            trash_count = 0
            try:
                req = urllib.request.Request("http://127.0.0.1:8080/api/stats", headers={"User-Agent": "SwachhBridge"})
                with urllib.request.urlopen(req, timeout=0.6) as resp:
                    npu_stats = json.loads(resp.read().decode("utf-8"))
                    fps = round(float(npu_stats.get("fps", 0.0)), 1)
                    trash_count = int(npu_stats.get("trash_count", 0))

                    with STATE_LOCK:
                        auto_enabled = LIVE_STATE.get("auto_divert", False)
                        cooldown = LIVE_STATE.get("auto_cooldown_sec", 8.0)

                    now = time.time()
                    if auto_enabled and last_seen_trash_count != -1 and trash_count > last_seen_trash_count and (now - last_divert_trigger_time) > cooldown:
                        last_divert_trigger_time = now
                        threading.Thread(target=run_full_diversion_cycle, args=(2.5,), daemon=True).start()

                    last_seen_trash_count = trash_count
            except Exception:
                pass

            core_temp = "N/A"
            try:
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as tf:
                    core_temp = f"{float(tf.read().strip()) / 1000.0:.1f}°C"
            except Exception:
                pass

            # Update LCD Display
            l1, l2 = "", ""
            if lcd:
                try:
                    current_gate = LIVE_STATE.get("gate_status", "NORMAL")
                    cur_pump = LIVE_STATE.get("pump_status", "OFF")
                    auto_tag = "ARM" if LIVE_STATE.get("auto_divert", False) else "MAN"
                    if current_gate == "DIVERTING":
                        l1 = ">> DIVERTING << "
                        l2 = f"TRASH:{trash_count:3d} [{auto_tag}]"
                    else:
                        d_str = f"{dist_ultra:4.1f}c"
                        if screen_cycle % 2 == 0:
                            l1 = f"TRASH:{trash_count:3d}  {d_str}"[:16]
                            l2 = f"W:{pct_water:4.1f}% [{auto_tag}] {cur_pump[:2]}"[:16]
                        else:
                            l1 = f"SURFACE: {d_str}    "[:16]
                            l2 = f"V:{v_water:5.3f}V NPU:OK"[:16]

                    lcd.write_string(l1.ljust(16), 0)
                    lcd.write_string(l2.ljust(16), 1)
                    screen_cycle += 1
                except Exception:
                    pass

            with STATE_LOCK:
                LIVE_STATE["camera_fps"] = fps
                LIVE_STATE["trash_diverted"] = trash_count
                LIVE_STATE["water_voltage"] = round(v_water, 4)
                LIVE_STATE["water_percentage"] = round(pct_water, 1)
                LIVE_STATE["ultrasonic_distance_cm"] = dist_ultra
                LIVE_STATE["water_depth_cm"] = depth_cm
                LIVE_STATE["lcd_line1"] = l1
                LIVE_STATE["lcd_line2"] = l2
                LIVE_STATE["core_temp"] = core_temp
                LIVE_STATE["last_update"] = time.time()

        except Exception as e:
            print(f"[WORKER ERROR]: {e}")

        time.sleep(0.4)


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
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
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
                invert = bool(data.get("invert", False))
                if target_state in ["ON", "OFF"]:
                    set_hardware_pump_relay(target_state == "ON", invert_polarity=invert)
                current = LIVE_STATE.get("pump_status", "OFF")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "state": current}).encode("utf-8"))
            except Exception as e:
                self.send_error(400, f"Error: {e}")
            return

        elif path == "/api/toggle_pump":
            try:
                current = LIVE_STATE.get("pump_status", "OFF")
                new_target = "OFF" if current == "ON" else "ON"
                set_hardware_pump_relay(new_target == "ON")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "state": LIVE_STATE.get("pump_status")}).encode("utf-8"))
            except Exception as e:
                self.send_error(400, f"Error: {e}")
            return

        elif path == "/api/set_servo_angle":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                data = json.loads(body)
                angle = float(data.get("angle", 0.0))
                print(f">> [API POST] /api/set_servo_angle received: {angle} deg")
                actuate_servo_to_angle(angle)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "ok",
                    "angle": LIVE_STATE.get("servo_angle"),
                    "duty_ns": LIVE_STATE.get("servo_duty_ns")
                }).encode("utf-8"))
            except Exception as e:
                self.send_error(400, f"Error: {e}")
            return

        elif path == "/api/return_home":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                data = json.loads(body) if body else {}
                home_angle = float(data.get("home_angle", LIVE_STATE.get("closed_angle", 0.0)))
                home_angle = max(0.0, min(180.0, home_angle))
                actuate_servo_to_angle(home_angle)
                with STATE_LOCK:
                    LIVE_STATE["gate_status"] = "NORMAL"
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "home_angle": home_angle}).encode("utf-8"))
            except Exception as e:
                self.send_error(400, f"Error: {e}")
            return

        elif path == "/api/force_close":
            with STATE_LOCK:
                closed_ang = LIVE_STATE.get("closed_angle", 0.0)
                LIVE_STATE["gate_status"] = "CLOSED"
            actuate_servo_to_angle(closed_ang)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(b'{"status":"ok","gate":"closed"}')
            return

        elif path == "/api/trigger_gate":
            threading.Thread(target=run_full_diversion_cycle, args=(2.5,), daemon=True).start()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(b'{"status":"ok","gate":"pwm_triggered"}')
            return

        elif path == "/api/test_servo_sweep":
            def _sweep():
                print(">> [SERVO SWEEP] Starting dual-pin test sweep: 0° -> 45° -> 90° -> 135° -> 180° -> 0°...")
                for ang in [0, 45, 90, 135, 180, 90, 0]:
                    actuate_servo_to_angle(ang)
                    time.sleep(0.8)
                print(">> [SERVO SWEEP] Test sweep complete.")
            threading.Thread(target=_sweep, daemon=True).start()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(b'{"status":"ok","sweep":"started"}')
            return

        elif path == "/api/toggle_auto_divert":
            with STATE_LOCK:
                LIVE_STATE["auto_divert"] = not LIVE_STATE.get("auto_divert", False)
                cur = LIVE_STATE["auto_divert"]
                closed_ang = LIVE_STATE.get("closed_angle", 0.0)
            if not cur:
                actuate_servo_to_angle(closed_ang)
                with STATE_LOCK:
                    LIVE_STATE["gate_status"] = "CLOSED"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "auto_divert": cur}).encode("utf-8"))
            return

        elif path == "/api/reset_trash_counter":
            with STATE_LOCK:
                LIVE_STATE["trash_diverted"] = 0
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(b'{"status":"ok","trash_diverted":0}')
            return

        elif path == "/api/camera_settings":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                data = json.loads(body)
                exp = data.get("exposure")
                gain = data.get("gain")
                vflip = data.get("vflip")
                hflip = data.get("hflip")
                set_hardware_camera_controls(exposure=exp, gain=gain, vflip=vflip, hflip=hflip)
                with STATE_LOCK:
                    if exp: LIVE_STATE["camera_exposure"] = int(exp)
                    if gain: LIVE_STATE["camera_gain"] = int(gain)
                    if vflip is not None: LIVE_STATE["camera_vflip"] = int(vflip)
                    if hflip is not None: LIVE_STATE["camera_hflip"] = int(hflip)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
            except Exception as e:
                self.send_error(400, f"Error: {e}")
            return

        self.send_error(404, "Not Found")


def main():
    print("=" * 65)
    print("  SWACHH-NAYAN: UNIVERSAL MULTI-PIN MASTER (PORT 8088)")
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
    f.write(server_code)

print("Regenerated server_live_final.py with Universal Multi-Pin Hardware Engine.")
