#!/usr/bin/env python3
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

RELAY_PINS = [54] # Physical Pin 5 (GPIO 54) ONLY
SERVO_GPIO_PINS = [48] # Physical Pin 12 (GPIO 48) fallback only

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
                            f.write(f"{pin}\n")
                        time.sleep(0.01)
                with open(f"{p_dir}/direction", "w") as f:
                    f.write("out\n")
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
                    f.write("0\n")
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
                    f.write("0\n")
            with open(f"{PWM_NODE}/period", "w") as f:
                f.write("20000000\n")
            try:
                with open(f"{PWM_NODE}/polarity", "w") as f:
                    f.write("normal\n")
            except Exception:
                pass
            with open(f"{PWM_NODE}/duty_cycle", "w") as f:
                f.write("1000000\n")
            with open(f"{PWM_NODE}/enable", "w") as f:
                f.write("1\n")

        return True
    except Exception as e:
        print(f"[PWM ERROR]: {e}")
        return False


def set_hardware_pump_relay(state_on: bool, invert_polarity: bool = False):
    init_all_pins()
    with RELAY_LOCK:
        val_str = "0\n" if (state_on if invert_polarity else not state_on) else "1\n"
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
                f.write(f"{duty_ns}\n")
            with open(f"{PWM_NODE}/enable", "w") as f:
                f.write("1\n")
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
                    fd.write("1\n")
                    fd.flush()
                time.sleep(pulse_high_s)
                for fd in open_fds:
                    fd.write("0\n")
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


HTML_DASHBOARD = r"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SWACHH-NAYAN LIVE AI | Industrial Studio Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #080c14;
            --surface-1: #0f172a;
            --surface-2: #1e293b;
            --surface-3: #27354f;
            --border: rgba(56, 189, 248, 0.16);
            --border-hover: rgba(56, 189, 248, 0.4);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent-cyan: #06b6d4;
            --accent-blue: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.25);
            --color-success: #10b981;
            --color-warning: #f59e0b;
            --color-alert: #ef4444;
            --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            --font-mono: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
            --radius-lg: 16px;
            --radius-md: 12px;
            --radius-sm: 8px;
            --shadow-card: 0 10px 30px -10px rgba(0, 0, 0, 0.5), 0 0 1px 1px rgba(255, 255, 255, 0.05);
            --transition-smooth: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }

        [data-theme="light"] {
            --bg-base: #f1f5f9;
            --surface-1: #ffffff;
            --surface-2: #f8fafc;
            --surface-3: #e2e8f0;
            --border: rgba(15, 23, 42, 0.12);
            --border-hover: rgba(56, 189, 248, 0.6);
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --text-muted: #94a3b8;
            --accent-glow: rgba(56, 189, 248, 0.15);
            --shadow-card: 0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 0 1px 1px rgba(0, 0, 0, 0.05);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: var(--font-sans);
            background-color: var(--bg-base);
            color: var(--text-primary);
            line-height: 1.5;
            min-height: 100vh;
            padding: 16px 24px;
            transition: background-color 0.3s ease, color 0.3s ease;
        }

        /* App Container */
        .dashboard-container {
            max-width: 1560px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        /* Top Header */
        .studio-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--surface-1);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 16px 24px;
            box-shadow: var(--shadow-card);
            flex-wrap: wrap;
            gap: 16px;
        }
        .header-brand {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .brand-logo {
            width: 44px;
            height: 44px;
            background: linear-gradient(135deg, #0ea5e9, #06b6d4);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 20px rgba(6, 182, 212, 0.4);
        }
        .brand-logo svg {
            width: 26px;
            height: 26px;
            fill: #ffffff;
        }
        .brand-title {
            font-size: 1.45rem;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: linear-gradient(90deg, #f8fafc, #38bdf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        [data-theme="light"] .brand-title {
            background: linear-gradient(90deg, #0f172a, #0284c7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .brand-subtitle {
            font-size: 0.78rem;
            color: var(--text-secondary);
            font-family: var(--font-mono);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .badge-chip {
            background: rgba(56, 189, 248, 0.14);
            color: var(--accent-blue);
            border: 1px solid rgba(56, 189, 248, 0.3);
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 0.7rem;
            font-weight: 700;
        }

        .header-meta {
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }
        .connection-pill {
            display: flex;
            align-items: center;
            gap: 8px;
            background: var(--surface-2);
            border: 1px solid var(--border);
            padding: 8px 14px;
            border-radius: 30px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .pulse-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: var(--color-success);
            box-shadow: 0 0 10px var(--color-success);
            animation: pulseLed 1.8s infinite;
        }
        @keyframes pulseLed {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1.1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }
        .btn-icon {
            background: var(--surface-2);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 8px 12px;
            border-radius: var(--radius-sm);
            cursor: pointer;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: var(--transition-smooth);
            font-size: 0.82rem;
        }
        .btn-icon:hover {
            border-color: var(--border-hover);
            background: var(--surface-3);
        }
        .btn-danger {
            background: rgba(239, 68, 68, 0.15);
            border-color: rgba(239, 68, 68, 0.4);
            color: var(--color-alert);
        }
        .btn-danger:hover {
            background: var(--color-alert);
            color: white;
        }

        /* Main Grid Layout */
        .dashboard-grid {
            display: grid;
            grid-template-columns: 12fr;
            gap: 20px;
        }
        @media (min-width: 1100px) {
            .hero-split-grid {
                display: grid;
                grid-template-columns: 7.5fr 4.5fr;
                gap: 20px;
            }
            .controls-split-grid {
                display: grid;
                grid-template-columns: 6fr 6fr;
                gap: 20px;
            }
            .telemetry-split-grid {
                display: grid;
                grid-template-columns: 7fr 5fr;
                gap: 20px;
            }
        }

        /* Generic Card Styles */
        .studio-card {
            background: var(--surface-1);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 20px;
            box-shadow: var(--shadow-card);
            transition: var(--transition-smooth);
            display: flex;
            flex-direction: column;
            position: relative;
            overflow: hidden;
        }
        .studio-card:hover {
            border-color: var(--border-hover);
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border);
        }
        .card-title-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .card-icon {
            font-size: 1.15rem;
            color: var(--accent-blue);
        }
        .card-title {
            font-size: 1.05rem;
            font-weight: 700;
            letter-spacing: -0.2px;
        }
        .status-pill {
            font-size: 0.72rem;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 20px;
            text-transform: uppercase;
            font-family: var(--font-mono);
            letter-spacing: 0.5px;
        }
        .status-idle { background: rgba(16, 185, 129, 0.15); color: var(--color-success); border: 1px solid rgba(16, 185, 129, 0.3); }
        .status-active { background: rgba(6, 182, 212, 0.15); color: var(--accent-cyan); border: 1px solid rgba(6, 182, 212, 0.3); }
        .status-warn { background: rgba(245, 158, 11, 0.15); color: var(--color-warning); border: 1px solid rgba(245, 158, 11, 0.3); }
        .status-alert { background: rgba(239, 68, 68, 0.15); color: var(--color-alert); border: 1px solid rgba(239, 68, 68, 0.3); }

        /* Camera Viewport */
        .camera-viewport {
            position: relative;
            width: 100%;
            height: 440px;
            background: #000000;
            border-radius: var(--radius-md);
            overflow: hidden;
            border: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .camera-img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            display: block;
            transition: opacity 0.2s ease;
        }
        .camera-overlay-top {
            position: absolute;
            top: 12px;
            left: 12px;
            right: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 10;
            pointer-events: none;
        }
        .camera-overlay-badge {
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #ffffff;
            font-family: var(--font-mono);
            font-size: 0.72rem;
            padding: 4px 10px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            gap: 6px;
            pointer-events: auto;
        }
        .camera-overlay-bottom {
            position: absolute;
            bottom: 12px;
            left: 12px;
            right: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 10;
            pointer-events: none;
        }
        .camera-toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 12px;
            padding-top: 10px;
            flex-wrap: wrap;
            gap: 10px;
        }
        .camera-buttons {
            display: flex;
            gap: 8px;
        }
        .rate-selector {
            display: flex;
            background: var(--surface-2);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 2px;
        }
        .rate-btn {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition-smooth);
        }
        .rate-btn.active {
            background: var(--accent-blue);
            color: #000000;
        }

        /* Servo Visualizations & Dial */
        .servo-viz-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 16px;
        }
        @media (max-width: 650px) {
            .servo-viz-container { grid-template-columns: 1fr; }
        }
        .viz-box {
            background: var(--surface-2);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 14px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            position: relative;
        }
        .viz-label {
            position: absolute;
            top: 10px;
            left: 12px;
            font-size: 0.72rem;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* SVG Dial */
        .dial-svg {
            width: 170px;
            height: 110px;
            margin-top: 12px;
        }
        .dial-track { fill: none; stroke: var(--surface-3); stroke-width: 12; stroke-linecap: round; }
        .dial-progress {
            fill: none;
            stroke: url(#cyanGrad);
            stroke-width: 12;
            stroke-linecap: round;
            stroke-dasharray: 251.2;
            stroke-dashoffset: 251.2;
            transition: stroke-dashoffset 0.35s ease;
        }
        .dial-needle {
            stroke: var(--accent-cyan);
            stroke-width: 3.5;
            stroke-linecap: round;
            transform-origin: 90px 85px;
            transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        .dial-value-text {
            font-family: var(--font-mono);
            font-size: 1.45rem;
            font-weight: 800;
            fill: var(--text-primary);
            text-anchor: middle;
        }

        /* Channel Gate Graphic */
        .channel-svg {
            width: 100%;
            height: 110px;
            margin-top: 12px;
        }

        /* Controls Form & Sliders */
        .control-row {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 14px;
        }
        .control-label {
            flex: 0 0 120px;
            font-size: 0.82rem;
            font-weight: 600;
            color: var(--text-secondary);
        }
        .slider-flex {
            flex: 1;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .studio-slider {
            flex: 1;
            -webkit-appearance: none;
            height: 8px;
            background: var(--surface-2);
            border: 1px solid var(--border);
            border-radius: 4px;
            outline: none;
        }
        .studio-slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            background: var(--accent-blue);
            cursor: pointer;
            box-shadow: 0 0 12px var(--accent-blue);
            transition: transform 0.1s;
        }
        .studio-slider::-webkit-slider-thumb:hover {
            transform: scale(1.15);
        }
        .num-input {
            width: 75px;
            background: var(--surface-2);
            border: 1px solid var(--border);
            color: var(--text-primary);
            font-family: var(--font-mono);
            font-size: 0.9rem;
            font-weight: 700;
            padding: 6px 10px;
            border-radius: var(--radius-sm);
            text-align: center;
        }

        .presets-row {
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }
        .preset-btn {
            flex: 1;
            min-width: 55px;
            background: var(--surface-2);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            padding: 6px;
            border-radius: var(--radius-sm);
            font-size: 0.78rem;
            font-family: var(--font-mono);
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition-smooth);
        }
        .preset-btn:hover {
            background: var(--surface-3);
            color: var(--text-primary);
            border-color: var(--border-hover);
        }

        /* DC Motor Power Card */
        .motor-hero-box {
            display: flex;
            align-items: center;
            justify-content: space-around;
            background: var(--surface-2);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 24px;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 20px;
        }
        .turbine-graphic {
            width: 120px;
            height: 120px;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .turbine-rotor {
            width: 100px;
            height: 100px;
            transition: transform 0.5s ease;
        }
        .turbine-running {
            animation: spinTurbine 1.0s linear infinite;
        }
        @keyframes spinTurbine {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        .motor-switch-group {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
        }
        .rocker-toggle {
            position: relative;
            width: 140px;
            height: 52px;
            background: var(--surface-3);
            border: 2px solid var(--border);
            border-radius: 30px;
            cursor: pointer;
            display: flex;
            align-items: center;
            padding: 4px;
            transition: var(--transition-smooth);
        }
        .rocker-toggle.on {
            background: rgba(16, 185, 129, 0.2);
            border-color: var(--color-success);
        }
        .rocker-thumb {
            width: 44px;
            height: 44px;
            background: #94a3b8;
            border-radius: 50%;
            transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1), background-color 0.25s;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
        }
        .rocker-toggle.on .rocker-thumb {
            transform: translateX(88px);
            background: var(--color-success);
            box-shadow: 0 0 16px var(--color-success);
        }
        .btn-action-row {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }
        .btn-action {
            flex: 1;
            padding: 12px 18px;
            border: none;
            border-radius: var(--radius-sm);
            font-size: 0.88rem;
            font-weight: 700;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: var(--transition-smooth);
        }
        .btn-primary {
            background: linear-gradient(135deg, #0284c7, #06b6d4);
            color: #ffffff;
            box-shadow: 0 4px 14px rgba(2, 132, 199, 0.3);
        }
        .btn-primary:hover {
            box-shadow: 0 6px 20px rgba(6, 182, 212, 0.45);
            transform: translateY(-1px);
        }
        .btn-secondary {
            background: var(--surface-2);
            border: 1px solid var(--border);
            color: var(--text-primary);
        }
        .btn-secondary:hover {
            background: var(--surface-3);
            border-color: var(--border-hover);
        }
        .btn-success {
            background: linear-gradient(135deg, #059669, #10b981);
            color: #ffffff;
        }
        .btn-muted {
            background: #334155;
            color: #cbd5e1;
        }

        /* Progress Bar */
        .progress-bar-container {
            width: 100%;
            height: 6px;
            background: var(--surface-3);
            border-radius: 3px;
            overflow: hidden;
            margin-top: 10px;
        }
        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #06b6d4, #10b981);
            width: 0%;
            transition: width 0.3s ease;
        }

        /* Metric Counters */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 12px;
            margin-top: 8px;
        }
        .metric-cell {
            background: var(--surface-2);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 12px;
            text-align: center;
        }
        .metric-title {
            font-size: 0.72rem;
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
        }
        .metric-value {
            font-family: var(--font-mono);
            font-size: 1.55rem;
            font-weight: 800;
            margin: 4px 0 2px 0;
            color: var(--accent-blue);
        }
        .metric-sub {
            font-size: 0.7rem;
            color: var(--text-muted);
        }

        /* Terminal Activity Log */
        .log-terminal {
            background: #04070d;
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 14px;
            height: 180px;
            overflow-y: auto;
            font-family: var(--font-mono);
            font-size: 0.76rem;
            color: #cbd5e1;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .log-entry { display: flex; gap: 8px; }
        .log-time { color: var(--text-muted); }
        .log-tag { font-weight: bold; border-radius: 3px; padding: 0 4px; }
        .tag-servo { color: var(--accent-cyan); }
        .tag-motor { color: var(--color-success); }
        .tag-vision { color: #a855f7; }
        .tag-sys { color: var(--accent-blue); }
        .tag-err { color: var(--color-alert); }

        /* Toast Container */
        .toast-container {
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
            pointer-events: none;
        }
        .toast {
            pointer-events: auto;
        }
        .toast {
            background: var(--surface-1);
            border: 1px solid var(--border);
            box-shadow: 0 10px 30px rgba(0,0,0,0.6);
            color: var(--text-primary);
            padding: 12px 18px;
            border-radius: var(--radius-sm);
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 10px;
            animation: slideInToast 0.3s ease;
        }
        @keyframes slideInToast {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
    </style>
</head>
<body>
    <!-- DIRECT SERVO OVERRIDE BAR -->
    <div class="servo-quick-bar" style="background: linear-gradient(90deg, #0369a1, #0284c7); padding: 10px 20px; display: flex; align-items: center; justify-content: space-between; gap: 12px; border-bottom: 2px solid #38bdf8; position: sticky; top: 0; z-index: 1000; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
        <div style="font-weight: 800; color: #fff; font-size: 0.9rem; letter-spacing: 0.5px; display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 1.2rem;">⚡</span> DIRECT SERVO HARDWARE CONTROL:
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <button onclick="directMoveServo(0)" style="padding: 7px 15px; background: #0f172a; color: #38bdf8; border: 1px solid #38bdf8; font-weight: 700; border-radius: 6px; cursor: pointer; font-size: 0.85rem;">0° (REST)</button>
            <button onclick="directMoveServo(45)" style="padding: 7px 15px; background: #0f172a; color: #38bdf8; border: 1px solid #38bdf8; font-weight: 700; border-radius: 6px; cursor: pointer; font-size: 0.85rem;">45° (QUARTER)</button>
            <button onclick="directMoveServo(90)" style="padding: 7px 15px; background: #38bdf8; color: #020617; border: 1px solid #38bdf8; font-weight: 800; border-radius: 6px; cursor: pointer; font-size: 0.85rem;">90° (DIVERT)</button>
            <button onclick="directMoveServo(135)" style="padding: 7px 15px; background: #0f172a; color: #38bdf8; border: 1px solid #38bdf8; font-weight: 700; border-radius: 6px; cursor: pointer; font-size: 0.85rem;">135° (WIDE)</button>
            <button onclick="directMoveServo(180)" style="padding: 7px 15px; background: #0f172a; color: #38bdf8; border: 1px solid #38bdf8; font-weight: 700; border-radius: 6px; cursor: pointer; font-size: 0.85rem;">180° (MAX)</button>
            <button onclick="simulateTrashDetection()" style="padding: 7px 16px; background: #ec4899; color: #ffffff; border: none; font-weight: 800; border-radius: 6px; cursor: pointer; font-size: 0.85rem; box-shadow: 0 2px 10px rgba(236, 72, 153, 0.4);">🎯 SIMULATE TRASH DETECT</button>
            <button onclick="triggerTestSweep()" style="padding: 7px 16px; background: #f59e0b; color: #020617; border: none; font-weight: 800; border-radius: 6px; cursor: pointer; font-size: 0.85rem;">🔄 RUN TEST SWEEP</button>
        </div>
    </div>

    <div class="dashboard-container">
        <!-- Dashboard Header -->
        <header class="studio-header">
            <div class="header-brand">
                <div class="brand-logo">
                    <svg viewBox="0 0 24 24">
                        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                    </svg>
                </div>
                <div>
                    <h1 class="brand-title">SWACHH-NAYAN LIVE AI</h1>
                    <div class="brand-subtitle">
                        <span>LUCKFOX PICO RV1103</span>
                        <span class="badge-chip">0.5T NPU</span>
                        <span class="badge-chip">SC3336 3MP</span>
                        <span class="badge-chip">HW PWM11</span>
                    </div>
                </div>
            </div>

            <div class="header-meta">
                <div class="connection-pill" id="connPill">
                    <span class="pulse-dot" id="connDot"></span>
                    <span id="connLabel">PICO CONNECTED (172.32.0.93)</span>
                </div>
                <button class="btn-icon" onclick="toggleTheme()" title="Toggle Light/Dark Theme">
                    <span id="themeIcon">☀️</span> <span id="themeLabel">Light</span>
                </button>
                <button class="btn-icon btn-danger" onclick="emergencyPark()" title="Stop all motors and return servo to 0°">
                    <span>🛑</span> <span>PARK ALL</span>
                </button>
            </div>
        </header>

        <!-- Main Layout Section -->
        <main class="dashboard-grid">
            
            <!-- Hero Top Row: Live AI Camera (Left) + Primary Counters (Right) -->
            <section class="hero-split-grid">
                
                <!-- Camera Feed Card -->
                <div class="studio-card">
                    <div class="card-header">
                        <div class="card-title-group">
                            <span class="card-icon">📷</span>
                            <h2 class="card-title">Live SC3336 3MP Camera & AI Vision Feed</h2>
                        </div>
                        <span class="status-pill status-idle" id="camStatusPill">STREAM ONLINE</span>
                    </div>

                    <div class="camera-viewport" id="camViewport">
                        <div class="camera-overlay-top">
                            <div class="camera-overlay-badge">
                                <span class="pulse-dot" style="background:#ef4444; box-shadow:0 0 8px #ef4444;"></span>
                                <span>LIVE SC3336 3MP</span>
                            </div>
                            <div class="camera-overlay-badge" id="aiInferenceBadge">
                                <span>AI: YOLOv5n INT8 (RV1103 NPU)</span>
                            </div>
                        </div>

                                                <img id="liveCamImg" class="camera-img" src="/snapshot.bmp" alt="Luckfox Pico MIPI CSI Feed" onerror="onCameraImgError()" />

                        <!-- REAL-TIME AI DETECTION HUD BANNER -->
                        <div class="camera-detection-banner" id="cameraDetectionBanner" style="position: absolute; top: 48px; left: 14px; right: 14px; background: rgba(15, 23, 42, 0.88); backdrop-filter: blur(8px); border: 1.5px solid #38bdf8; border-radius: 8px; padding: 9px 15px; display: flex; align-items: center; justify-content: space-between; z-index: 10; box-shadow: 0 4px 20px rgba(0,0,0,0.6);">
                            <div style="display: flex; align-items: center; gap: 9px;">
                                <span class="pulse-dot" id="detectPulseDot" style="background: #10b981; box-shadow: 0 0 10px #10b981; width: 10px; height: 10px;"></span>
                                <span style="font-size: 0.85rem; font-weight: 800; color: #f8fafc; letter-spacing: 0.3px;" id="detectStatusText">CANAL CLEAR: SCANNING FOR FLOATING WASTE</span>
                            </div>
                            <div style="font-size: 0.75rem; color: #38bdf8; font-weight: 700; text-transform: uppercase;" id="detectConfText">YOLOv5n REAL-TIME NPU</div>
                        </div>

                        <div class="camera-overlay-bottom">
                            <div class="camera-overlay-badge" id="fpsLatencyBadge">
                                <span>4.7 FPS | 212 ms</span>
                            </div>
                            <div class="camera-overlay-badge" id="frameTimeBadge">
                                <span>Frame: Syncing...</span>
                            </div>
                        </div>
                    </div>

                    <div class="camera-toolbar">
                        <div class="camera-buttons">
                            <button class="btn-icon" onclick="manualRefreshSnapshot()">
                                <span>🔄</span> Refresh Snapshot
                            </button>
                            <button class="btn-icon" id="btnPauseStream" onclick="toggleStreamPause()">
                                <span>⏸</span> Pause Feed
                            </button>
                            <button class="btn-icon" onclick="toggleFullscreen()">
                                <span>⛶</span> Fullscreen
                            </button>
                        </div>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="font-size:0.75rem; color:var(--text-muted); font-weight:600;">REFRESH RATE:</span>
                            <div class="rate-selector">
                                <button class="rate-btn active" id="rate250" onclick="setRefreshInterval(250)">250ms</button>
                                <button class="rate-btn" id="rate500" onclick="setRefreshInterval(500)">500ms</button>
                                <button class="rate-btn" id="rate1000" onclick="setRefreshInterval(1000)">1s</button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Right Column: Operational Metrics & Auto-Divert -->
                <div style="display:flex; flex-direction:column; gap:20px;">
                    <!-- Trash Collection Counter Card -->
                    <div class="studio-card">
                        <div class="card-header">
                            <div class="card-title-group">
                                <span class="card-icon">♻️</span>
                                <h3 class="card-title">Waste Collection Telemetry</h3>
                            </div>
                            <button class="btn-icon" onclick="resetTrashCounter()" style="padding:4px 8px; font-size:0.75rem;">
                                <span>↺</span> Reset
                            </button>
                        </div>

                        <div class="metrics-grid">
                            <div class="metric-cell">
                                <div class="metric-title">Diverted Items</div>
                                <div class="metric-value" id="trashCountDisplay">0</div>
                                <div class="metric-sub">Verified Pieces</div>
                            </div>
                            <div class="metric-cell">
                                <div class="metric-title">Estimated Mass</div>
                                <div class="metric-value" id="massDisplay" style="color:var(--color-success);">0.00 kg</div>
                                <div class="metric-sub">Plastics Captured</div>
                            </div>
                        </div>

                        <div style="margin-top:16px;">
                            <div style="display:flex; justify-content:space-between; font-size:0.78rem; margin-bottom:6px;">
                                <span style="color:var(--text-secondary); font-weight:600;">Water Level (HC-SR04)</span>
                                <span id="waterDepthTxt" style="font-family:var(--font-mono); font-weight:bold; color:var(--accent-cyan);">6.0 cm (Normal)</span>
                            </div>
                            <div class="progress-bar-container">
                                <div class="progress-bar-fill" id="waterProgress" style="width: 25%;"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Auto Divert & PWM Architecture Card -->
                    <div class="studio-card" style="flex:1;">
                        <div class="card-header">
                            <div class="card-title-group">
                                <span class="card-icon">⚙️</span>
                                <h3 class="card-title">Auto-Divert & Edge NPU Mode</h3>
                            </div>
                            <span class="status-pill status-active" id="autoModePill">MANUAL STANDBY</span>
                        </div>

                        <div style="display:flex; align-items:center; justify-content:space-between; background:var(--surface-2); padding:14px; border-radius:var(--radius-md); border:1px solid var(--border);">
                            <div>
                                <div style="font-weight:700; font-size:0.9rem;">Edge AI Auto-Diversion</div>
                                <div style="font-size:0.75rem; color:var(--text-secondary);">Switches flap automatically when NPU detects trash</div>
                            </div>
                            <button class="btn-action btn-secondary" id="btnToggleAuto" onclick="toggleAutoDivert()" style="max-width:130px; padding:8px 14px;">
                                <span>🛡️</span> <span id="autoBtnText">ARM AUTO</span>
                            </button>
                        </div>

                        <div style="margin-top:16px; font-size:0.78rem; color:var(--text-secondary); display:flex; flex-direction:column; gap:8px;">
                            <div style="display:flex; justify-content:space-between; border-bottom:1px solid var(--border); padding-bottom:6px;">
                                <span>Hardware PWM Chip:</span>
                                <span style="font-family:var(--font-mono); color:var(--accent-blue);">pwmchip11 (Pin 4)</span>
                            </div>
                            <div style="display:flex; justify-content:space-between; border-bottom:1px solid var(--border); padding-bottom:6px;">
                                <span>PWM Period & Freq:</span>
                                <span style="font-family:var(--font-mono); color:var(--accent-blue);">20,000,000 ns (50.0 Hz)</span>
                            </div>
                            <div style="display:flex; justify-content:space-between;">
                                <span>Current Pulse Duty:</span>
                                <span style="font-family:var(--font-mono); color:var(--color-success);" id="pwmDutyTxt">1,000,000 ns (1.000 ms)</span>
                            </div>
                        </div>
                    </div>
                </div>

            </section>

            <!-- Middle Section: Dedicated Servo Motor Control & Dedicated DC Motor Control -->
            <section class="controls-split-grid">
                
                <!-- 1. Dedicated Servo Motor Control Panel -->
                <div class="studio-card">
                    <div class="card-header">
                        <div class="card-title-group">
                            <span class="card-icon">🎛️</span>
                            <h2 class="card-title">MG996R Servo Flap Control Panel</h2>
                        </div>
                        <span class="status-pill status-idle" id="servoOpStatusPill">IDLE (0.0°)</span>
                    </div>

                    <!-- Dual Servo Visualizations -->
                    <div class="servo-viz-container">
                        <!-- Left: Radial Angle Gauge -->
                        <div class="viz-box">
                            <span class="viz-label">Angular Position</span>
                            <svg class="dial-svg" viewBox="0 0 180 110">
                                <defs>
                                    <linearGradient id="cyanGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                                        <stop offset="0%" stop-color="#0284c7" />
                                        <stop offset="100%" stop-color="#06b6d4" />
                                    </linearGradient>
                                </defs>
                                <!-- Background Arc (0 to 180 deg) -->
                                <path class="dial-track" d="M 20 90 A 70 70 0 0 1 160 90" />
                                <!-- Progress Arc -->
                                <path id="dialProgressPath" class="dial-progress" d="M 20 90 A 70 70 0 0 1 160 90" />
                                <!-- Pointer Needle -->
                                <line id="dialNeedle" class="dial-needle" x1="90" y1="85" x2="25" y2="85" />
                                <circle cx="90" cy="85" r="7" fill="var(--accent-blue)" />
                                <!-- Center readout -->
                                <text id="dialAngleText" class="dial-value-text" x="90" y="70">0°</text>
                            </svg>
                            <div style="font-size:0.7rem; color:var(--text-muted); margin-top:-6px; font-family:var(--font-mono);">
                                Confirmed: <b id="confirmedAngleVal" style="color:var(--accent-blue);">0.0°</b> | Commanded: <b id="commandedAngleVal">0.0°</b>
                            </div>
                        </div>

                        <!-- Right: Physical Gate Cross-Section -->
                        <div class="viz-box">
                            <span class="viz-label">Storm-Drain Gate Simulation</span>
                            <svg class="channel-svg" viewBox="0 0 200 110">
                                <!-- Water Canal Borders -->
                                <rect x="10" y="25" width="180" height="60" rx="6" fill="#0c1929" stroke="var(--border)" stroke-width="1.5"/>
                                <!-- Flow stream ripples -->
                                <path d="M 20 45 Q 40 40 60 45 T 100 45 T 140 45" fill="none" stroke="rgba(56, 189, 248, 0.3)" stroke-width="2"/>
                                <path d="M 25 65 Q 45 60 65 65 T 105 65 T 145 65" fill="none" stroke="rgba(56, 189, 248, 0.3)" stroke-width="2"/>
                                <!-- Diverter Chute opening (top right) -->
                                <path d="M 130 25 L 175 10" stroke="#f59e0b" stroke-width="3" stroke-dasharray="4,3"/>
                                <text x="140" y="18" fill="#f59e0b" font-size="8" font-family="var(--font-mono)">COLLECTION CHUTE</text>
                                <!-- Flow direction arrow -->
                                <text x="25" y="80" fill="var(--text-muted)" font-size="9" font-family="var(--font-mono)">FLOW &gt;&gt;&gt;</text>
                                <!-- Movable Gate Flap attached to pivot (130, 85) -->
                                <g id="gateFlapG" transform="rotate(0, 130, 85)">
                                    <line x1="130" y1="85" x2="130" y2="28" stroke="#ef4444" stroke-width="5" stroke-linecap="round"/>
                                    <circle cx="130" cy="85" r="5" fill="#f8fafc"/>
                                </g>
                            </svg>
                            <div style="font-size:0.7rem; color:var(--text-muted); margin-top:-6px; font-family:var(--font-mono);">
                                Flap State: <b id="flapVisualState" style="color:var(--color-success);">CLOSED (FLOW NORMAL)</b>
                            </div>
                        </div>
                    </div>

                    <!-- Target Angle Slider & Numeric Input -->
                    <div class="control-row">
                        <label class="control-label" for="servoAngleInput">Target Angle (°):</label>
                        <div class="slider-flex">
                            <input type="range" class="studio-slider" id="servoAngleSlider" min="0" max="180" value="90" oninput="onSliderInput(this.value)" onchange="directMoveServo(this.value)">
                            <input type="number" class="num-input" id="servoAngleInput" min="0" max="180" value="90" oninput="onNumInput(this.value)" onchange="directMoveServo(this.value)">
                        </div>
                    </div>

                    <!-- Quick Preset Angle Buttons -->
                    <div class="presets-row">
                        <button class="preset-btn" onclick="selectPresetAngle(0)">0° (Closed)</button>
                        <button class="preset-btn" onclick="selectPresetAngle(45)">45° (Quarter)</button>
                        <button class="preset-btn" onclick="selectPresetAngle(90)">90° (Divert)</button>
                        <button class="preset-btn" onclick="selectPresetAngle(135)">135° (Wide)</button>
                        <button class="preset-btn" onclick="selectPresetAngle(180)">180° (Max)</button>
                    </div>

                    <!-- Auto-Return Configuration Controls -->
                    <div style="background:var(--surface-2); border:1px solid var(--border); border-radius:var(--radius-md); padding:14px; margin-bottom:16px;">
                        <div style="font-size:0.8rem; font-weight:700; color:var(--accent-blue); margin-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
                            <span>AUTOMATIC RETURN WORKFLOW SETTINGS</span>
                            <label style="display:flex; align-items:center; gap:6px; cursor:pointer; font-size:0.75rem; color:var(--text-primary);">
                                <input type="checkbox" id="autoReturnCheck" checked style="accent-color:var(--accent-blue); transform:scale(1.15);">
                                Auto-Return Enabled
                            </label>
                        </div>

                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                            <div>
                                <label style="font-size:0.75rem; color:var(--text-secondary); display:block; margin-bottom:4px;">Home/Rest Angle (°)</label>
                                <input type="number" class="num-input" id="homeAngleInput" min="0" max="180" value="0" style="width:100%;">
                            </div>
                            <div>
                                <label style="font-size:0.75rem; color:var(--text-secondary); display:block; margin-bottom:4px;">Hold Duration (sec)</label>
                                <input type="number" class="num-input" id="holdDurationInput" min="0.5" max="30" step="0.5" value="2.5" style="width:100%;">
                            </div>
                        </div>

                        <div class="progress-bar-container" style="margin-top:12px;">
                            <div class="progress-bar-fill" id="servoWorkflowProgress"></div>
                        </div>
                    </div>

                    <!-- Action Buttons -->
                    <div class="btn-action-row">
                        <button class="btn-action btn-primary" id="btnMoveServo" onclick="executeServoMotionWorkflow()">
                            <span>▶</span> MOVE SERVO
                        </button>
                        <button class="btn-action btn-info" onclick="triggerTestSweep()" style="background:#0284c7; color:#fff;" title="Run automated hardware sweep test">
                            <span>🔄</span> TEST SWEEP (0° ➔ 180°)
                        </button>
                        <button class="btn-action btn-secondary" onclick="returnServoHome()">
                            <span>🏠</span> RETURN HOME
                        </button>
                        <button class="btn-action btn-secondary" onclick="forceServoClose()">
                            <span>🔒</span> 0° CLOSE
                        </button>
                    </div>
                </div>

                <!-- 2. Dedicated DC Motor Control Panel -->
                <div class="studio-card">
                    <div class="card-header">
                        <div class="card-title-group">
                            <span class="card-icon">⚡</span>
                            <h2 class="card-title">12V DC Motor / Pump Control</h2>
                        </div>
                        <span class="status-pill status-active" id="motorStatusPill">RUNNING (ON)</span>
                    </div>

                    <!-- Turbine Hero Box with Rotating Impeller -->
                    <div class="motor-hero-box">
                        <div class="turbine-graphic">
                            <svg class="turbine-rotor turbine-running" id="turbineSvg" viewBox="0 0 100 100">
                                <circle cx="50" cy="50" r="46" fill="none" stroke="var(--border)" stroke-width="2"/>
                                <!-- 6-Blade Industrial Impeller -->
                                <g fill="url(#cyanGrad)">
                                    <path d="M 50 50 C 45 30 35 20 50 8 C 55 20 52 35 50 50 Z"/>
                                    <path d="M 50 50 C 70 45 80 35 92 50 C 80 55 65 52 50 50 Z"/>
                                    <path d="M 50 50 C 55 70 65 80 50 92 C 45 80 48 65 50 50 Z"/>
                                    <path d="M 50 50 C 30 55 20 65 8 50 C 20 45 35 48 50 50 Z"/>
                                </g>
                                <circle cx="50" cy="50" r="14" fill="#1e293b" stroke="var(--accent-blue)" stroke-width="3"/>
                                <circle cx="50" cy="50" r="5" fill="#f8fafc"/>
                            </svg>
                        </div>

                        <div class="motor-switch-group">
                            <div class="rocker-toggle on" id="motorRocker" onclick="toggleDcMotorFromRocker()" title="Click to toggle DC Motor power">
                                <div class="rocker-thumb">
                                    <svg viewBox="0 0 24 24" width="20" height="20" fill="#ffffff">
                                        <path d="M12 2v10M18.4 6.6a9 9 0 1 1-12.8 0"/>
                                    </svg>
                                </div>
                            </div>
                            <div id="motorStatusTxt" style="font-weight:700; font-size:0.95rem; color:var(--color-success); font-family:var(--font-mono);">
                                MOTOR CONFIRMED: ON
                            </div>
                        </div>
                    </div>

                    <!-- Discrete ON / OFF Buttons -->
                    <div class="btn-action-row" style="margin-bottom:16px;">
                        <button class="btn-action btn-success" id="btnMotorOn" onclick="setDcMotorState('ON')">
                            <span>⚡</span> SWITCH MOTOR ON
                        </button>
                        <button class="btn-action btn-muted" id="btnMotorOff" onclick="setDcMotorState('OFF')">
                            <span>🛑</span> SWITCH MOTOR OFF
                        </button>
                    </div>

                    <!-- Hardware Circuitry & Safety Details -->
                    <div style="background:var(--surface-2); border:1px solid var(--border); border-radius:var(--radius-md); padding:14px; font-size:0.78rem; color:var(--text-secondary); display:flex; flex-direction:column; gap:8px;">
                        <div style="display:flex; justify-content:space-between; border-bottom:1px solid var(--border); padding-bottom:6px;">
                            <span>Hardware Interface:</span>
                            <span style="font-family:var(--font-mono); color:var(--accent-blue);">Pin 5 / GPIO54 (5V Optocoupler Relay)</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; border-bottom:1px solid var(--border); padding-bottom:6px;">
                            <span>Power Supply Bus:</span>
                            <span style="font-family:var(--font-mono); color:var(--text-primary);">12V DC (5A Regulated Adapter)</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; border-bottom:1px solid var(--border); padding-bottom:6px;">
                            <span>Dry-Run Interlock:</span>
                            <span style="font-family:var(--font-mono); color:var(--color-success);">ARMED (Auto-cutout if empty)</span>
                        </div>
                        <div style="display:flex; justify-content:space-between;">
                            <span>Last Motor Command:</span>
                            <span style="font-family:var(--font-mono); color:var(--text-primary);" id="motorLastCmdTxt">Initialized Active (12V Flowing)</span>
                        </div>
                    </div>
                </div>

            </section>

            <!-- Bottom Section: Real-Time Event Audit Log -->
            <section class="studio-card">
                <div class="card-header">
                    <div class="card-title-group">
                        <span class="card-icon">📋</span>
                        <h3 class="card-title">Live Hardware Audit Trail & Activity Log</h3>
                    </div>
                    <div style="display:flex; gap:8px;">
                        <button class="btn-icon" onclick="clearActivityLog()" style="padding:4px 8px; font-size:0.75rem;">
                            <span>🗑️</span> Clear Log
                        </button>
                    </div>
                </div>

                <div class="log-terminal" id="activityLogBox">
                    <div class="log-entry">
                        <span class="log-time">[BOOT]</span>
                        <span class="log-tag tag-sys">[SYSTEM]</span>
                        <span>SWACHH-NAYAN Live Studio UI Initialized. Connected to Luckfox Pico at 172.32.0.93.</span>
                    </div>
                </div>
            </section>

        </main>
    </div>

    <!-- Toast Notification Container -->
    <div class="toast-container" id="toastContainer"></div>

    <script>
        // System Configuration
        let PICO_IP = window.location.hostname === "172.32.0.93" ? "172.32.0.93" : (window.location.hostname || "172.32.0.93");
        let PICO_PORT = window.location.port === "8088" ? "8088" : "8088";
        let BASE_URL = (window.location.protocol === "file:") ? "http://172.32.0.93:8088" : "";

        // State Machine
        let isServoBusy = false;
        let isMotorBusy = false;
        let isStreamPaused = false;
        let streamRefreshMs = 250;
        let streamTimer = null;
        let telemetryTimer = null;
        let confirmedServoAngle = 0.0;
        let commandedServoAngle = 90.0;
        let confirmedMotorState = "ON";

        // Initialization
        window.addEventListener("DOMContentLoaded", () => {
            initStream();
            startTelemetryPolling();
            updateServoVisuals(0.0);
            logEvent("SYS", "Hardware polling worker connected to port 8088.");
        });

        // Theme Switcher
        function toggleTheme() {
            const html = document.documentElement;
            const current = html.getAttribute("data-theme") || "dark";
            const next = current === "dark" ? "light" : "dark";
            html.setAttribute("data-theme", next);
            document.getElementById("themeIcon").innerText = next === "dark" ? "☀️" : "🌙";
            document.getElementById("themeLabel").innerText = next === "dark" ? "Light" : "Dark";
        }

        // Toast Notifications
        function showToast(message, type = "info") {
            const container = document.getElementById("toastContainer");
            const toast = document.createElement("div");
            toast.className = "toast";
            const icons = { info: "ℹ️", success: "✅", warn: "⚠️", error: "❌" };
            toast.innerHTML = `<span>${icons[type] || "ℹ️"}</span><span>${message}</span>`;
            container.appendChild(toast);
            setTimeout(() => {
                toast.style.opacity = "0";
                toast.style.transform = "translateX(100%)";
                setTimeout(() => toast.remove(), 300);
            }, 3200);
        }

        // Activity Logger
        function logEvent(tag, message) {
            const logBox = document.getElementById("activityLogBox");
            const entry = document.createElement("div");
            entry.className = "log-entry";
            const now = new Date().toTimeString().split(" ")[0];
            const tagClasses = {
                SERVO: "tag-servo",
                MOTOR: "tag-motor",
                VISION: "tag-vision",
                SYS: "tag-sys",
                ERR: "tag-err"
            };
            entry.innerHTML = `<span class="log-time">[${now}]</span><span class="log-tag ${tagClasses[tag] || "tag-sys"}">[${tag}]</span><span>${message}</span>`;
            logBox.appendChild(entry);
            logBox.scrollTop = logBox.scrollHeight;
        }

        function clearActivityLog() {
            document.getElementById("activityLogBox").innerHTML = "";
            logEvent("SYS", "Activity log cleared.");
        }

        // Camera Feed Pipeline (Dual-Buffer Smooth Refresh)
        function initStream() {
            if (streamTimer) clearInterval(streamTimer);
            if (isStreamPaused) return;

            streamTimer = setInterval(() => {
                refreshCameraFrame();
            }, streamRefreshMs);
        }

        function refreshCameraFrame() {
            if (isStreamPaused) return;
            const img = document.getElementById("liveCamImg");
            const nextImg = new Image();
            const timestamp = Date.now();
            nextImg.src = BASE_URL + "/snapshot.bmp?t=" + timestamp;
            nextImg.onload = () => {
                img.src = nextImg.src;
                document.getElementById("camStatusPill").innerText = "STREAM ONLINE";
                document.getElementById("camStatusPill").className = "status-pill status-idle";
                const d = new Date(timestamp);
                document.getElementById("frameTimeBadge").innerText = "Frame: " + d.toTimeString().split(" ")[0] + "." + String(d.getMilliseconds()).padStart(3, '0');
            };
            nextImg.onerror = () => {
                onCameraImgError();
            };
        }

        function manualRefreshSnapshot() {
            refreshCameraFrame();
            showToast("Camera frame refreshed", "info");
        }

        function toggleStreamPause() {
            isStreamPaused = !isStreamPaused;
            const btn = document.getElementById("btnPauseStream");
            if (isStreamPaused) {
                if (streamTimer) clearInterval(streamTimer);
                btn.innerHTML = "<span>▶</span> Resume Feed";
                document.getElementById("camStatusPill").innerText = "PAUSED";
                document.getElementById("camStatusPill").className = "status-pill status-warn";
                showToast("Live camera feed paused", "warn");
            } else {
                btn.innerHTML = "<span>⏸</span> Pause Feed";
                initStream();
                showToast("Live camera feed resumed", "info");
            }
        }

        function setRefreshInterval(ms) {
            streamRefreshMs = ms;
            document.querySelectorAll(".rate-btn").forEach(b => b.classList.remove("active"));
            if (ms === 250) document.getElementById("rate250").classList.add("active");
            if (ms === 500) document.getElementById("rate500").classList.add("active");
            if (ms === 1000) document.getElementById("rate1000").classList.add("active");
            initStream();
        }

        function toggleFullscreen() {
            const vp = document.getElementById("camViewport");
            if (!document.fullscreenElement) {
                vp.requestFullscreen().catch(err => alert("Fullscreen error: " + err.message));
            } else {
                document.exitFullscreen();
            }
        }

        function onCameraImgError() {
            document.getElementById("camStatusPill").innerText = "CONNECTING...";
            document.getElementById("camStatusPill").className = "status-pill status-alert";
        }

        // Servo Dial & Visual Gauge Helpers
        function updateServoVisuals(angle) {
            const clamped = Math.max(0, Math.min(180, parseFloat(angle)));
            // Arc progress (total arc is 251.2)
            const arcFrac = clamped / 180.0;
            const offset = 251.2 * (1.0 - arcFrac);
            document.getElementById("dialProgressPath").style.strokeDashoffset = offset;
            
            // Needle rotation: from 0 deg (needle at 0° which is pointing left/down) to 180 deg
            // Base needle x1=90 y1=85 x2=25 y2=85 (pointing 180° in standard math, or 0° of dial)
            document.getElementById("dialNeedle").style.transform = `rotate(${clamped}deg)`;
            document.getElementById("dialAngleText").textContent = Math.round(clamped) + "°";
            document.getElementById("confirmedAngleVal").textContent = clamped.toFixed(1) + "°";

            // Update physical gate cross-section flap rotation
            document.getElementById("gateFlapG").setAttribute("transform", `rotate(${clamped}, 130, 85)`);
            const flapState = document.getElementById("flapVisualState");
            if (clamped < 10) {
                flapState.innerText = "CLOSED (FLOW NORMAL)";
                flapState.style.color = "var(--color-success)";
            } else if (clamped > 60) {
                flapState.innerText = `DIVERTING ACTIVE (${Math.round(clamped)}°)`;
                flapState.style.color = "var(--color-alert)";
            } else {
                flapState.innerText = `PARTIAL (${Math.round(clamped)}°)`;
                flapState.style.color = "var(--color-warning)";
            }
        }

        function onSliderInput(val) {
            commandedServoAngle = parseFloat(val);
            document.getElementById("servoAngleInput").value = val;
            document.getElementById("commandedAngleVal").textContent = parseFloat(val).toFixed(1) + "°";
        }

        function onNumInput(val) {
            let v = parseFloat(val);
            if (isNaN(v)) v = 0;
            v = Math.max(0, Math.min(180, v));
            commandedServoAngle = v;
            document.getElementById("servoAngleSlider").value = v;
            document.getElementById("commandedAngleVal").textContent = v.toFixed(1) + "°";
        }

        let directServoDebounce = null;
        async function directMoveServo(angle) {
            const clamped = Math.max(0, Math.min(180, parseFloat(angle)));
            commandedServoAngle = clamped;
            updateServoVisuals(clamped);
            document.getElementById("servoOpStatusPill").innerText = `MOVING TO ${clamped.toFixed(0)}°`;
            document.getElementById("servoOpStatusPill").className = "status-pill status-active";

            if (directServoDebounce) clearTimeout(directServoDebounce);
            directServoDebounce = setTimeout(async () => {
                try {
                    logEvent("SERVO", `Sending angle ${clamped.toFixed(1)}° to controller...`);
                    const res = await fetch(BASE_URL + "/api/set_servo_angle", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ angle: clamped })
                    });
                    if (res.ok) {
                        const data = await res.json().catch(() => ({}));
                        confirmedServoAngle = clamped;
                        updateServoVisuals(clamped);
                        document.getElementById("servoOpStatusPill").innerText = `HOLDING AT ${clamped.toFixed(0)}°`;
                        document.getElementById("servoOpStatusPill").className = "status-pill status-idle";
                        showToast(`Servo positioned at ${clamped.toFixed(0)}°`, "success");
                        logEvent("SERVO", `Physical servo confirmed at ${clamped.toFixed(1)}° (duty: ${data.duty_ns || 'calibrated'} ns).`);
                    } else {
                        throw new Error("HTTP " + res.status);
                    }
                } catch (err) {
                    showToast("Servo command failed: " + err.message, "error");
                    logEvent("ERR", "Servo command error: " + err.message);
                }
            }, 100);
        }

        async function selectPresetAngle(ang) {
            onSliderInput(ang);
            await directMoveServo(ang);
        }

        async function triggerTestSweep() {
            showToast("Initiating Physical Servo Sweep Test...", "info");
            logEvent("SERVO", "Hardware Test Sweep initiated: 0° -> 45° -> 90° -> 135° -> 180° -> 0°");
            document.getElementById("servoOpStatusPill").innerText = "TEST SWEEPING...";
            document.getElementById("servoOpStatusPill").className = "status-pill status-warn";
            try {
                const res = await fetch(BASE_URL + "/api/test_servo_sweep", { method: "POST" });
                if (res.ok) {
                    showToast("Physical servo test sweep running on hardware!", "success");
                }
            } catch (err) {
                showToast("Sweep trigger error: " + err.message, "error");
            }
        }

        // Servo Motor Control: Complete Validated Workflow
        async function executeServoMotionWorkflow() {
            if (isServoBusy) {
                showToast("Servo motion already in progress! Please wait.", "warn");
                return;
            }

            const target = Math.max(0, Math.min(180, parseFloat(document.getElementById("servoAngleInput").value)));
            const home = Math.max(0, Math.min(180, parseFloat(document.getElementById("homeAngleInput").value)));
            const holdSec = Math.max(0.2, Math.min(30, parseFloat(document.getElementById("holdDurationInput").value)));
            const autoReturn = document.getElementById("autoReturnCheck").checked;

            isServoBusy = true;
            document.getElementById("btnMoveServo").disabled = true;
            document.getElementById("servoOpStatusPill").innerText = `MOVING TO ${target}°`;
            document.getElementById("servoOpStatusPill").className = "status-pill status-active";
            logEvent("SERVO", `Initiating motion: Target=${target}°, Home=${home}°, Hold=${holdSec}s, AutoReturn=${autoReturn}`);

            try {
                // 1. Send Target Angle Command to Backend
                const res = await fetch(BASE_URL + "/api/set_servo_angle", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ angle: target })
                });

                if (!res.ok) throw new Error("Hardware rejected angle command");

                confirmedServoAngle = target;
                updateServoVisuals(target);
                showToast(`Servo moved to ${target}°`, "success");

                if (autoReturn) {
                    // 2. Holding Phase with Animated Progress Bar
                    document.getElementById("servoOpStatusPill").innerText = `HOLDING (${holdSec}s)`;
                    document.getElementById("servoOpStatusPill").className = "status-pill status-warn";
                    logEvent("SERVO", `Holding position at ${target}° for ${holdSec}s...`);

                    const prog = document.getElementById("servoWorkflowProgress");
                    prog.style.width = "0%";
                    const startT = Date.now();
                    const holdMs = holdSec * 1000;

                    await new Promise(resolve => {
                        const interval = setInterval(() => {
                            const elapsed = Date.now() - startT;
                            const pct = Math.min(100, (elapsed / holdMs) * 100);
                            prog.style.width = pct + "%";
                            if (elapsed >= holdMs) {
                                clearInterval(interval);
                                resolve();
                            }
                        }, 50);
                    });

                    // 3. Return to Home Phase
                    document.getElementById("servoOpStatusPill").innerText = `RETURNING TO ${home}°`;
                    document.getElementById("servoOpStatusPill").className = "status-pill status-active";
                    logEvent("SERVO", `Auto-Return triggered: Moving back to home position ${home}°...`);

                    const retRes = await fetch(BASE_URL + "/api/set_servo_angle", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ angle: home })
                    });

                    if (!retRes.ok) throw new Error("Hardware failed on return command");

                    confirmedServoAngle = home;
                    updateServoVisuals(home);
                    showToast(`Servo returned home to ${home}°`, "success");
                    logEvent("SERVO", `Servo successfully returned home to ${home}°. Cycle complete.`);
                }
            } catch (err) {
                showToast("Servo Error: " + err.message, "error");
                logEvent("ERR", "Servo motion failure: " + err.message);
            } finally {
                isServoBusy = false;
                document.getElementById("btnMoveServo").disabled = false;
                document.getElementById("servoWorkflowProgress").style.width = "0%";
                document.getElementById("servoOpStatusPill").innerText = `IDLE (${confirmedServoAngle.toFixed(1)}°)`;
                document.getElementById("servoOpStatusPill").className = "status-pill status-idle";
            }
        }

        async function returnServoHome() {
            if (isServoBusy) return;
            const home = Math.max(0, Math.min(180, parseFloat(document.getElementById("homeAngleInput").value)));
            try {
                await fetch(BASE_URL + "/api/set_servo_angle", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ angle: home })
                });
                confirmedServoAngle = home;
                updateServoVisuals(home);
                showToast(`Servo returned home to ${home}°`, "success");
                logEvent("SERVO", `Manual Return Home executed: position=${home}°`);
            } catch (err) {
                showToast("Return Home failed: " + err.message, "error");
            }
        }

        async function forceServoClose() {
            try {
                await fetch(BASE_URL + "/api/force_close", { method: "POST" });
                confirmedServoAngle = 0.0;
                updateServoVisuals(0.0);
                showToast("Servo closed to 0°", "info");
                logEvent("SERVO", "Force close executed: 0.0°");
            } catch (e) {
                showToast("Force close error", "error");
            }
        }

        // DC Motor Control Workflow (ON / OFF / Toggle)
        async function setDcMotorState(targetState) {
            if (isMotorBusy) return;
            isMotorBusy = true;

            const pill = document.getElementById("motorStatusPill");
            const txt = document.getElementById("motorStatusTxt");
            pill.innerText = "COMMANDING...";
            pill.className = "status-pill status-warn";
            txt.innerText = `SWITCHING TO: ${targetState}...`;
            txt.style.color = "var(--color-warning)";

            logEvent("MOTOR", `Command sent: Turn DC Motor ${targetState} (Relay Pin 5 / GPIO54)`);

            try {
                // Send explicit ON / OFF state command to physical GPIO54 relay
                const res = await fetch(BASE_URL + "/api/set_motor", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ state: targetState })
                });

                if (res.ok) {
                    const data = await res.json().catch(() => ({ state: targetState }));
                    const finalState = data.state || targetState;
                    confirmedMotorState = finalState;
                    applyMotorVisualState(finalState);
                    showToast(`12V DC Motor confirmed: ${finalState}`, "success");
                    logEvent("MOTOR", `12V DC Motor confirmed ${finalState} (GPIO54 relay switch active).`);
                    document.getElementById("motorLastCmdTxt").innerText = `Switched ${finalState} at ` + new Date().toTimeString().split(" ")[0];
                } else {
                    throw new Error("Relay controller response error");
                }
            } catch (err) {
                showToast("Motor Control Error: " + err.message, "error");
                logEvent("ERR", "DC Motor toggle error: " + err.message);
                applyMotorVisualState(confirmedMotorState);
            } finally {
                isMotorBusy = false;
            }
        }

        function toggleDcMotorFromRocker() {
            const next = confirmedMotorState === "ON" ? "OFF" : "ON";
            setDcMotorState(next);
        }

        function applyMotorVisualState(state) {
            const rocker = document.getElementById("motorRocker");
            const pill = document.getElementById("motorStatusPill");
            const txt = document.getElementById("motorStatusTxt");
            const turbine = document.getElementById("turbineSvg");

            if (state === "ON") {
                rocker.classList.add("on");
                pill.innerText = "RUNNING (ON)";
                pill.className = "status-pill status-active";
                txt.innerText = "MOTOR CONFIRMED: ON";
                txt.style.color = "var(--color-success)";
                turbine.classList.add("turbine-running");
            } else {
                rocker.classList.remove("on");
                pill.innerText = "STOPPED (OFF)";
                pill.className = "status-pill status-idle";
                txt.innerText = "MOTOR CONFIRMED: OFF";
                txt.style.color = "var(--text-muted)";
                turbine.classList.remove("turbine-running");
            }
        }

        // Auto-Divert Toggle
        async function toggleAutoDivert() {
            try {
                const res = await fetch(BASE_URL + "/api/toggle_auto_divert", { method: "POST" });
                const d = await res.json();
                const isAuto = d.auto_divert;
                updateAutoDivertUi(isAuto);
                showToast("Auto-divert mode: " + (isAuto ? "ARMED" : "STANDBY"), "info");
                logEvent("SYS", "Auto-Divert mode switched to: " + (isAuto ? "ARMED (AUTO ON)" : "STANDBY (MANUAL)"));
            } catch (e) {
                showToast("Failed to toggle auto divert", "error");
            }
        }

        function updateAutoDivertUi(isAuto) {
            const pill = document.getElementById("autoModePill");
            const btn = document.getElementById("autoBtnText");
            if (isAuto) {
                pill.innerText = "ARMED (AUTO ON)";
                pill.className = "status-pill status-alert";
                btn.innerText = "STANDBY";
            } else {
                pill.innerText = "MANUAL STANDBY";
                pill.className = "status-pill status-active";
                btn.innerText = "ARM AUTO";
            }
        }

        async function resetTrashCounter() {
            if (!confirm("Are you sure you want to reset the trash counter?")) return;
            try {
                await fetch(BASE_URL + "/api/reset_trash_counter", { method: "POST" });
                document.getElementById("trashCountDisplay").innerText = "0";
                document.getElementById("massDisplay").innerText = "0.00 kg";
                showToast("Trash counter reset to zero", "info");
                logEvent("VISION", "Trash collection counter reset to 0.");
            } catch (e) {
                showToast("Failed to reset counter", "error");
            }
        }

        async function emergencyPark() {
            showToast("Emergency Park: Halting DC Motor & Closing Flap...", "warn");
            logEvent("SYS", "EMERGENCY PARK TRIGGERED: Halting pump and resetting flap to 0°.");
            try {
                await setDcMotorState("OFF");
                await forceServoClose();
            } catch (e) {
                console.error(e);
            }
        }

        // Live Telemetry Poller
        
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

        function startTelemetryPolling() {
            if (telemetryTimer) clearInterval(telemetryTimer);
            telemetryTimer = setInterval(pollTelemetry, 1000);
            pollTelemetry();
        }

        async function pollTelemetry() {
            try {
                const res = await fetch(BASE_URL + "/api/live_telemetry");
                if (!res.ok) throw new Error("Telemetry HTTP " + res.status);
                const d = await res.json();

                // 1. Connection status
                document.getElementById("connDot").style.backgroundColor = "var(--color-success)";
                document.getElementById("connLabel").innerText = "PICO CONNECTED (172.32.0.93)";

                // 2. Counters & Metrics
                document.getElementById("trashCountDisplay").innerText = d.trash_diverted || 0;

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

                const mass = ((d.trash_diverted || 0) * 0.024).toFixed(2);
                document.getElementById("massDisplay").innerText = mass + " kg";

                // 3. Water Depth (HC-SR04)
                const dist = d.ultrasonic_distance_cm || 0;
                const depth = d.water_depth_cm || 0;
                const pct = Math.max(0, Math.min(100, d.water_percentage || 0));
                document.getElementById("waterDepthTxt").innerText = `${depth.toFixed(1)} cm (Distance: ${dist.toFixed(1)} cm)`;
                document.getElementById("waterProgress").style.width = pct + "%";

                // 4. Hardware PWM11 Stats
                document.getElementById("pwmDutyTxt").innerText = `${(d.servo_duty_ns || 1000000).toLocaleString()} ns (${(d.servo_pulse_ms || 1.0).toFixed(3)} ms)`;

                // 5. FPS & Latency
                const fps = d.camera_fps || 0;
                document.getElementById("fpsLatencyBadge").innerText = `${fps.toFixed(1)} FPS | Core: ${d.core_temp || "45°C"}`;

                // 6. Confirmed Motor State from Backend
                if (d.pump_status && !isMotorBusy) {
                    confirmedMotorState = d.pump_status;
                    applyMotorVisualState(d.pump_status);
                }

                // 7. Confirmed Servo Angle from Backend
                if (d.servo_angle !== undefined && !isServoBusy) {
                    confirmedServoAngle = d.servo_angle;
                    updateServoVisuals(d.servo_angle);
                    document.getElementById("servoOpStatusPill").innerText = `IDLE (${confirmedServoAngle.toFixed(1)}°)`;
                }

                // 8. Auto-divert status
                if (d.auto_divert !== undefined) {
                    updateAutoDivertUi(d.auto_divert);
                }

            } catch (err) {
                document.getElementById("connDot").style.backgroundColor = "var(--color-alert)";
                document.getElementById("connLabel").innerText = "DISCONNECTED (Retrying...)";
            }
        }
    </script>
</body>
</html>
"""


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
