#!/usr/bin/env python3
"""
Swachh-Nayan: Live Production Dashboard & Telemetry Master
Zero-Mock Real-Time Integration for Luckfox Pico RV1103.
Includes Rockchip Hardware PWM11 (50Hz / 20ms) MG996R Servo Engine & Camera Tuning.
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

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from hal.ads1115 import ADS1115
from hal.ultrasonic import UltrasonicSensor
from hal.lcd1602 import LCD1602

PORT = 8088
PWM_CHIP = "/sys/class/pwm/pwmchip11"
PWM_NODE = "/sys/class/pwm/pwmchip11/pwm0"

# Global Shared Hardware State (100% Real Live Readings)
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
    "pump_status": "ON",
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


def init_hardware_pwm():
    """Initializes Rockchip Hardware PWM11 on Physical Pin 4 (GPIO1_C7 / Pin 55) for 50Hz (20ms) RC servo."""
    try:
        # Unexport gpio55 if it was exported to prevent pinmux conflict
        if os.path.exists("/sys/class/gpio/gpio55"):
            os.system("echo 55 > /sys/class/gpio/unexport 2>/dev/null")

        if not os.path.exists(PWM_NODE):
            if os.path.exists(f"{PWM_CHIP}/export"):
                with open(f"{PWM_CHIP}/export", "w") as f:
                    f.write("0\n")
                time.sleep(0.05)

        if not os.path.exists(PWM_NODE):
            print("[PWM ERROR] /sys/class/pwm/pwmchip11/pwm0 not found.")
            return False

        # Read current period
        try:
            with open(f"{PWM_NODE}/period", "r") as f:
                cur_p = int(f.read().strip())
        except Exception:
            cur_p = 0

        # Configure 50Hz = 20,000,000 ns
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

        print("[PWM] Rockchip Hardware PWM11 successfully verified on Pin 4 (50Hz / 20ms period).")
        return True
    except Exception as e:
        print(f"[PWM ERROR] Failed to initialize hardware PWM11: {e}")
        return False


def set_hardware_pwm_duty_ns(duty_ns: int):
    """Sets duty cycle directly in nanoseconds on Hardware PWM11."""
    init_hardware_pwm()
    duty_ns = max(400000, min(2600000, int(duty_ns)))
    try:
        with open(f"{PWM_NODE}/duty_cycle", "w") as f:
            f.write(f"{duty_ns}\n")
        with open(f"{PWM_NODE}/enable", "w") as f:
            f.write("1\n")
        return True
    except Exception as e:
        print(f"[PWM ERROR] Failed to set duty_cycle {duty_ns}ns: {e}")
        return False


def actuate_servo_to_angle(angle_deg: float):
    """
    Converts angle (0 to 180 degrees) to hardware PWM duty cycle in nanoseconds.
    MG996R Calibration:
      0°   -> 1,000,000 ns (1.00 ms) - Resting normal flow
      45°  -> 1,250,000 ns (1.25 ms) - Quarter open
      90°  -> 1,500,000 ns (1.50 ms) - Waste diversion open
      135° -> 1,750,000 ns (1.75 ms) - Wide open
      180° -> 2,000,000 ns (2.00 ms) - Max travel
    """
    clamped_angle = max(0.0, min(180.0, float(angle_deg)))
    duty_ns = int(1000000 + (clamped_angle / 180.0) * 1000000)
    pulse_ms = duty_ns / 1000000.0
    with SERVO_LOCK:
        set_hardware_pwm_duty_ns(duty_ns)
        with STATE_LOCK:
            LIVE_STATE["servo_angle"] = round(clamped_angle, 1)
            LIVE_STATE["servo_pulse_ms"] = round(pulse_ms, 3)
            LIVE_STATE["servo_duty_ns"] = duty_ns
            LIVE_STATE["pwm_active"] = True


def set_servo_pulse_direct(pulse_ms: float):
    """Sets direct pulse width in milliseconds (supports 0.5ms to 2.5ms extended travel)."""
    clamped_pulse = max(0.4, min(2.6, float(pulse_ms)))
    duty_ns = int(clamped_pulse * 1000000)
    angle = max(0.0, min(180.0, (clamped_pulse - 1.0) / 1.0 * 180.0))
    with SERVO_LOCK:
        set_hardware_pwm_duty_ns(duty_ns)
        with STATE_LOCK:
            LIVE_STATE["servo_angle"] = round(angle, 1)
            LIVE_STATE["servo_pulse_ms"] = round(clamped_pulse, 3)
            LIVE_STATE["servo_duty_ns"] = duty_ns
            LIVE_STATE["pwm_active"] = True


def run_full_diversion_cycle(hold_seconds: float = 2.5):
    """Actuates flap from closed_angle to divert_angle, holds for duration, then returns to closed_angle."""
    with STATE_LOCK:
        if LIVE_STATE.get("gate_status") == "DIVERTING":
            return # Already running
        LIVE_STATE["gate_status"] = "DIVERTING"
        closed_ang = LIVE_STATE.get("closed_angle", 0.0)
        divert_ang = LIVE_STATE.get("divert_angle", 90.0)
        
    print(f">> [SERVO ACTUATION] Moving flap from {closed_ang}° to {divert_ang}° DIVERT (Hold: {hold_seconds}s)...")
    actuate_servo_to_angle(divert_ang)

    # Notify local C++ app to increment trash diversion count if reachable
    try:
        req = urllib.request.Request("http://127.0.0.1:8080/api/trigger_gate", data=b"", method="POST")
        urllib.request.urlopen(req, timeout=0.8)
    except Exception:
        pass

    time.sleep(hold_seconds)
    print(f">> [SERVO ACTUATION] Returning flap to {closed_ang}° CLOSED position...")
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
    """Continuous worker polling physical sensors, driving hardware PWM, and syncing LCD."""
    print("[HARDWARE WORKER] Initializing Hardware PWM11, ADS1115, HC-SR04, and 16x2 LCD...")

    # Initialize Hardware PWM 11 on Pin 4
    init_hardware_pwm()
    actuate_servo_to_angle(0.0)

    # Initialize camera hardware defaults
    set_hardware_camera_controls(exposure=800, gain=2048, vflip=1, hflip=1)

    adc = ADS1115(i2c_bus=3, address=0x48)
    ultra = UltrasonicSensor(trig_pin=53, echo_pin=52, channel_depth_cm=22.0)
    lcd = LCD1602(i2c_bus=3, address=0x27)

    lcd.clear()
    lcd.write_string("SWACHH-NAYAN".center(16), 0)
    lcd.write_string("LIVE DASHBOARD".center(16), 1)
    time.sleep(1.0)

    screen_cycle = 0
    last_seen_trash_count = -1
    last_divert_trigger_time = 0.0

    while True:
        try:
            # 1. Read ADS1115 channel 0 (HW-038 water level sensor)
            v_water, pct_water = adc.read_water_level(channel=0)

            # 2. Ping HC-SR04 ultrasonic sensor
            dist_ultra = ultra.measure_raw_distance_cm()
            depth_cm = round(max(0.0, 22.0 - dist_ultra), 1) if dist_ultra is not None else 0.0

            # 3. Fetch live stats from local NPU AI vision process (port 8080)
            fps = 0.0
            trash_count = 0
            pump_status = "ON"
            try:
                req = urllib.request.Request("http://127.0.0.1:8080/api/stats", headers={"User-Agent": "SwachhBridge"})
                with urllib.request.urlopen(req, timeout=0.8) as resp:
                    npu_stats = json.loads(resp.read().decode("utf-8"))
                    fps = round(float(npu_stats.get("fps", 0.0)), 1)
                    trash_count = int(npu_stats.get("trash_count", 0))
                    pump_status = npu_stats.get("pump_status", "ON")

                    # Connect Vision Detection to Physical Flap Actuation (Debounced & Toggleable)
                    with STATE_LOCK:
                        auto_enabled = LIVE_STATE.get("auto_divert", False)
                        cooldown = LIVE_STATE.get("auto_cooldown_sec", 8.0)

                    now = time.time()
                    if auto_enabled and last_seen_trash_count != -1 and trash_count > last_seen_trash_count and (now - last_divert_trigger_time) > cooldown:
                        last_divert_trigger_time = now
                        print(f">> [VISION DETECTED TRASH] Count increased to {trash_count}! Auto-Actuating flap (ARMED)...")
                        threading.Thread(target=run_full_diversion_cycle, args=(2.5,), daemon=True).start()

                    last_seen_trash_count = trash_count
            except Exception:
                pass

            # 4. Read core temperature
            core_temp = "N/A"
            try:
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    core_temp = f"{float(f.read().strip()) / 1000.0:.1f}°C"
            except Exception:
                pass

            # Format LCD display strings
            current_gate = LIVE_STATE.get("gate_status", "NORMAL")
            auto_tag = "ARM" if LIVE_STATE.get("auto_divert", False) else "MAN"
            if current_gate == "DIVERTING":
                l1 = ">> DIVERTING << "
                l2 = f"TRASH:{trash_count:3d} [{auto_tag}]"
            else:
                d_str = f"{dist_ultra:4.1f}c" if dist_ultra is not None else "N/A"
                if screen_cycle % 2 == 0:
                    l1 = f"TRASH:{trash_count:3d}  {d_str}"[:16]
                    l2 = f"W:{pct_water:4.1f}% [{auto_tag}] {pump_status[:2]}"[:16]
                else:
                    l1 = f"SURFACE: {d_str}    "[:16]
                    l2 = f"V:{v_water:5.3f}V NPU:OK"[:16]

            # Update physical LCD
            lcd.write_string(l1.ljust(16), 0)
            lcd.write_string(l2.ljust(16), 1)
            screen_cycle += 1

            # Update global state
            with STATE_LOCK:
                LIVE_STATE["camera_fps"] = fps
                LIVE_STATE["trash_diverted"] = trash_count
                LIVE_STATE["pump_status"] = pump_status
                LIVE_STATE["water_voltage"] = round(v_water, 4)
                LIVE_STATE["water_percentage"] = round(pct_water, 1)
                LIVE_STATE["ultrasonic_distance_cm"] = dist_ultra if dist_ultra is not None else 0.0
                LIVE_STATE["water_depth_cm"] = depth_cm
                LIVE_STATE["lcd_line1"] = l1
                LIVE_STATE["lcd_line2"] = l2
                LIVE_STATE["core_temp"] = core_temp
                LIVE_STATE["last_update"] = time.time()

        except Exception as e:
            print(f"[HARDWARE WORKER ERROR]: {e}")

        time.sleep(0.5)


HTML_DASHBOARD = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Swachh-Nayan | Live Edge AI & Sensor Dashboard</title>
    <style>
        :root {
            --bg: #0b0f19;
            --card-bg: #131b2e;
            --border: #22304d;
            --accent-blue: #38bdf8;
            --accent-green: #22c55e;
            --accent-red: #ef4444;
            --accent-amber: #f59e0b;
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: var(--bg); color: var(--text-main); min-height: 100vh; padding: 20px; }
        .container { max-width: 1300px; margin: 0 auto; }
        header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 16px; margin-bottom: 24px; flex-wrap: wrap; gap: 12px; }
        .logo-wrap { display: flex; align-items: center; gap: 14px; }
        .logo-icon { font-size: 2rem; background: #0369a1; padding: 8px 12px; border-radius: 12px; }
        h1 { font-size: 1.5rem; letter-spacing: 0.5px; font-weight: 800; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .subtitle { font-size: 0.8rem; color: var(--text-sub); }
        .badge { padding: 6px 14px; border-radius: 20px; font-size: 0.78rem; font-weight: 700; text-transform: uppercase; }
        .badge-live { background: rgba(34, 197, 94, 0.15); border: 1px solid var(--accent-green); color: var(--accent-green); }
        .grid { display: grid; grid-template-columns: 1.15fr 1fr; gap: 20px; }
        @media (max-width: 950px) { .grid { grid-template-columns: 1fr; } }
        .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 14px; padding: 20px; margin-bottom: 20px; }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
        .card-header h2 { font-size: 1.05rem; font-weight: 600; color: #e2e8f0; }
        .camera-container { width: 100%; aspect-ratio: 4/3; background: #000; border-radius: 10px; overflow: hidden; border: 1px solid var(--border); position: relative; }
        .camera-container img { width: 100%; height: 100%; object-fit: cover; display: block; transition: filter 0.15s ease; }
        .camera-fps-tag { position: absolute; top: 12px; left: 12px; background: rgba(0,0,0,0.7); color: var(--accent-blue); padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: bold; font-family: monospace; }
        
        /* Camera Tuning Controls */
        .camera-tuning-box { margin-top: 14px; background: #090e1a; border: 1px solid var(--border); border-radius: 10px; padding: 14px; }
        .tuning-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
        .slider-wrap { display: flex; flex-direction: column; gap: 4px; }
        .slider-header { display: flex; justify-content: space-between; font-size: 0.75rem; font-weight: 600; color: var(--text-sub); }
        .slider-header span b { color: var(--accent-blue); font-family: monospace; }
        input[type="range"] { width: 100%; accent-color: var(--accent-blue); cursor: pointer; }
        
        .preset-buttons { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
        .btn-preset { padding: 6px 12px; background: #1e293b; border: 1px solid var(--border); color: #cbd5e1; border-radius: 6px; font-size: 0.75rem; font-weight: 600; cursor: pointer; transition: 0.2s; }
        .btn-preset:hover { background: #334155; color: #fff; }
        .btn-preset.active { background: #0284c7; color: white; border-color: #38bdf8; }

        .checkbox-row { display: flex; gap: 16px; align-items: center; font-size: 0.78rem; color: var(--text-sub); }
        .checkbox-row label { display: flex; align-items: center; gap: 6px; cursor: pointer; }

        .metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
        .metric-card { background: #0b1120; border: 1px solid var(--border); border-radius: 10px; padding: 16px; }
        .metric-card.full-width { grid-column: span 2; }
        .metric-label { font-size: 0.75rem; text-transform: uppercase; color: var(--text-sub); font-weight: 600; margin-bottom: 6px; display: block; }
        .metric-value { font-size: 1.7rem; font-weight: 800; color: #f8fafc; }
        .metric-desc { font-size: 0.75rem; color: var(--text-sub); margin-top: 4px; display: block; }
        .text-green { color: var(--accent-green) !important; }
        .text-blue { color: var(--accent-blue) !important; }
        .text-amber { color: var(--accent-amber) !important; }
        .text-red { color: var(--accent-red) !important; }

        .progress-bar { width: 100%; height: 8px; background: #1e293b; border-radius: 4px; overflow: hidden; margin: 8px 0; }
        .progress-fill { height: 100%; background: var(--accent-blue); transition: width 0.3s; }

        .lcd-mirror { background: #14532d; border: 3px solid #166534; border-radius: 8px; padding: 12px 18px; font-family: "Courier New", Courier, monospace; color: #86efac; font-size: 1.15rem; font-weight: bold; letter-spacing: 2px; text-shadow: 0 0 4px #4ade80; box-shadow: inset 0 0 10px rgba(0,0,0,0.6); }

        .btn-group { display: flex; gap: 12px; margin-top: 10px; }
        .btn { flex: 1; padding: 12px 16px; border: none; border-radius: 8px; font-weight: 700; cursor: pointer; font-size: 0.85rem; transition: all 0.2s; display: flex; align-items: center; justify-content: center; gap: 8px; }
        .btn-divert { background: #0284c7; color: white; }
        .btn-divert:hover { background: #0369a1; }
        .btn-pump { background: #334155; color: white; }
        .btn-pump:hover { background: #475569; }

        /* Servo Diagnostic & PWM Telemetry Section */
        .servo-diag-box { background: #090e1a; border: 1px solid var(--border); border-radius: 10px; padding: 16px; margin-top: 14px; }
        .pwm-badge-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #1e293b; }
        .pwm-chip-tag { background: rgba(56, 189, 248, 0.15); border: 1px solid var(--accent-blue); color: var(--accent-blue); padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: bold; font-family: monospace; }
        .servo-btn-bar { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
        .btn-servo-angle { padding: 8px 12px; background: #1e293b; border: 1px solid var(--border); color: #cbd5e1; border-radius: 6px; font-size: 0.78rem; font-weight: bold; cursor: pointer; transition: 0.15s; }
        .btn-servo-angle:hover { background: #0284c7; color: white; border-color: #38bdf8; }
        
        .pulse-subheading { font-size: 0.75rem; font-weight: 600; color: var(--text-sub); margin-top: 12px; margin-bottom: 6px; display: block; text-transform: uppercase; }

        .wiring-notice { background: rgba(245, 158, 11, 0.08); border-left: 3px solid var(--accent-amber); padding: 10px 14px; font-size: 0.75rem; color: #cbd5e1; margin-top: 14px; border-radius: 0 6px 6px 0; line-height: 1.5; }
        .wiring-notice b { color: #f8fafc; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-wrap">
                <div class="logo-icon">🌊</div>
                <div>
                    <h1>SWACHH-NAYAN LIVE PRODUCTION DASHBOARD</h1>
                    <p class="subtitle">Real-Time Edge-Vision Storm-Drain Trash Diverter &bull; Luckfox Pico RV1103</p>
                </div>
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
                <span class="badge" style="background: rgba(56, 189, 248, 0.15); border: 1px solid var(--accent-blue); color: var(--accent-blue);">
                    PWM11 &bull; 50.0 Hz SILICON ENGINE
                </span>
                <span class="badge badge-live">100% REAL HARDWARE &bull; NO MOCK</span>
            </div>
        </header>

        <div class="grid">
            <!-- Left: SC3336 Live Camera & Tuning Suite -->
            <div>
                <div class="card">
                    <div class="card-header">
                        <h2>📹 SC3336 Live Camera (RV1103 NPU YOLO)</h2>
                        <span style="font-size:0.75rem; color:#94a3b8;">Core Temp: <b id="coreTemp">--</b></span>
                    </div>
                    <div class="camera-container">
                        <img id="liveCam" src="/snapshot.bmp" alt="Live Camera Stream">
                        <div class="camera-fps-tag" id="fpsTag">-- FPS</div>
                    </div>

                    <!-- Hardware & Visual Tuning Suite -->
                    <div class="camera-tuning-box">
                        <div style="font-size:0.8rem; font-weight:bold; color:#e2e8f0; margin-bottom:10px;">
                            🎛️ Camera Brightness, Contrast & Sensor Registers
                        </div>

                        <!-- Presets -->
                        <div class="preset-buttons">
                            <button class="btn-preset active" onclick="applyPreset('studio')">💡 Balanced Studio (Recommended)</button>
                            <button class="btn-preset" onclick="applyPreset('bright')">☀️ High Brightness</button>
                            <button class="btn-preset" onclick="applyPreset('night')">🌙 Low-Light Boost</button>
                            <button class="btn-preset" onclick="applyPreset('raw')">🔄 Reset Sensor</button>
                        </div>

                        <!-- Hardware Sliders -->
                        <div class="tuning-grid">
                            <div class="slider-wrap">
                                <div class="slider-header">
                                    <span>Sensor Exposure Register</span>
                                    <span><b id="expVal">800</b></span>
                                </div>
                                <input type="range" id="expSlider" min="100" max="1350" step="25" value="800" oninput="onHardwareSliderChange()">
                            </div>

                            <div class="slider-wrap">
                                <div class="slider-header">
                                    <span>Analogue Gain Register</span>
                                    <span><b id="gainVal">2048</b></span>
                                </div>
                                <input type="range" id="gainSlider" min="256" max="8192" step="128" value="2048" oninput="onHardwareSliderChange()">
                            </div>

                            <div class="slider-wrap">
                                <div class="slider-header">
                                    <span>Visual Contrast Boost</span>
                                    <span><b id="contrastVal">115%</b></span>
                                </div>
                                <input type="range" id="contrastSlider" min="80" max="200" step="5" value="115" oninput="updateCssFilter()">
                            </div>

                            <div class="slider-wrap">
                                <div class="slider-header">
                                    <span>Visual Brightness Boost</span>
                                    <span><b id="brightVal">105%</b></span>
                                </div>
                                <input type="range" id="brightSlider" min="80" max="180" step="5" value="105" oninput="updateCssFilter()">
                            </div>
                        </div>

                        <!-- Flips -->
                        <div class="checkbox-row">
                            <label>
                                <input type="checkbox" id="vflipCheck" checked onchange="onHardwareSliderChange()">
                                <span>Vertical Flip (180°)</span>
                            </label>
                            <label>
                                <input type="checkbox" id="hflipCheck" checked onchange="onHardwareSliderChange()">
                                <span>Horizontal Flip (Mirror)</span>
                            </label>
                            <label>
                                <input type="checkbox" id="wbCheck" checked onchange="updateCssFilter()">
                                <span>Auto White-Balance Neutralizer</span>
                            </label>
                        </div>
                    </div>
                </div>

                <!-- Physical LCD Mirror -->
                <div class="card">
                    <div class="card-header">
                        <h2>📟 Physical 16x2 I2C LCD Display (Hardware Mirror)</h2>
                        <span style="font-size:0.75rem; color:#94a3b8;">Address 0x27 via BSS138</span>
                    </div>
                    <div class="lcd-mirror">
                        <div id="lcdLine1">SWACHH-NAYAN    </div>
                        <div id="lcdLine2">INITIALIZING... </div>
                    </div>
                </div>
            </div>

            <!-- Right: Real Sensors Telemetry & Controls -->
            <div>
                <div class="card">
                    <div class="card-header">
                        <h2>📊 Live Sensor Telemetry (Zero-Mock)</h2>
                    </div>
                    <div class="metric-grid">
                        <!-- Total Trash -->
                        <div class="metric-card full-width">
                            <span class="metric-label">Recyclable Plastics Diverted</span>
                            <div class="metric-value text-blue" id="trashCount">0</div>
                            <span class="metric-desc">Classified & tracked live by RV1103 NPU YOLO</span>
                        </div>

                        <!-- HC-SR04 Ultrasonic Distance -->
                        <div class="metric-card">
                            <span class="metric-label">Drain Surface Clearance</span>
                            <div class="metric-value" id="ultraDist">-- cm</div>
                            <span class="metric-desc">HC-SR04 (Pin 6 TRIG / Pin 7 ECHO)</span>
                        </div>

                        <!-- Calculated Water Depth -->
                        <div class="metric-card">
                            <span class="metric-label">Drain Water Depth</span>
                            <div class="metric-value text-green" id="waterDepth">-- cm</div>
                            <span class="metric-desc">Channel Mount Height: 22.0 cm</span>
                        </div>

                        <!-- HW-038 Water Level Sensor via ADS1115 -->
                        <div class="metric-card full-width">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span class="metric-label">HW-038 Water Contact Level</span>
                                <span id="waterVolt" style="font-size:0.8rem; font-family:monospace; color:#38bdf8;">0.12 V</span>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill" id="waterProgress" style="width: 0%;"></div>
                            </div>
                            <div style="display:flex; justify-content:space-between; font-size:0.8rem; color:#94a3b8;">
                                <span>ADS1115 A0 Channel</span>
                                <span id="waterPct" style="font-weight:bold; color:#fff;">0%</span>
                            </div>
                        </div>

                        <!-- Actuators State -->
                        <div class="metric-card">
                            <span class="metric-label">12V Water Pump</span>
                            <div class="metric-value text-green" id="pumpStatus">ON</div>
                            <span class="metric-desc">5V Relay (Pin 5 / GPIO54)</span>
                        </div>

                        <div class="metric-card">
                            <span class="metric-label">MG996R Diverter Gate</span>
                            <div class="metric-value" id="gateStatus">NORMAL</div>
                            <span class="metric-desc">Pin 4 / Rockchip Hardware PWM11</span>
                        </div>
                    </div>
                </div>

                <!-- Physical Hardware Controls & Rockchip PWM11 Servo Engine -->
                <div class="card">
                    <div class="card-header">
                        <h2>⚙️ MG996R Flap Engine (Rockchip Hardware PWM11)</h2>
                    </div>

                    <!-- Automated Vision Diversion Mode Control Panel -->
                    <div style="background: #090e1a; border: 1px solid var(--border); border-radius: 10px; padding: 14px; margin-bottom: 14px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                            <span style="font-size:0.85rem; font-weight:bold; color:#e2e8f0;">🛡️ Automated Vision Diversion Trigger</span>
                            <span class="badge" id="autoModeBadge" style="background:rgba(245, 158, 11, 0.15); border:1px solid var(--accent-amber); color:var(--accent-amber); font-size:0.75rem;">STANDBY (MANUAL ONLY)</span>
                        </div>
                        <div style="display:flex; gap:10px; align-items:center;">
                            <button class="btn" id="btnToggleAuto" onclick="toggleAutoDivert()" style="background:#334155; padding:10px 14px; font-size:0.82rem;">
                                ⏸️ Mode: STANDBY (Click to ARM Auto-Divert)
                            </button>
                            <button class="btn" onclick="resetTrashCounter()" style="background:#1e293b; border:1px solid var(--border); padding:10px 14px; font-size:0.82rem; max-width:140px;">
                                🔄 Reset Count
                            </button>
                        </div>
                        <div style="font-size:0.73rem; color:#94a3b8; margin-top:8px; line-height:1.4;">
                            <b>Why Standby?</b> While stationary objects remain in front of the camera, the YOLO AI detects them continuously. Standby mode stops repetitive actuation. Toggle to <b>ARMED</b> for real-time automatic storm-drain sorting.
                        </div>
                    </div>
                    
                    <div class="btn-group">
                        <button class="btn" onclick="forceCloseFlap()" style="background:#059669; color:white;">
                            <span>🔒</span> Force Close (<b id="btnClosedDeg">0°</b>)
                        </button>
                        <button class="btn btn-divert" onclick="triggerGate()">
                            <span>🚨</span> Trigger Divert (<b id="btnDivertDeg">90°</b>)
                        </button>
                        <button class="btn btn-pump" onclick="togglePump()" style="max-width:140px;">
                            <span>🔄</span> 12V Pump
                        </button>
                    </div>

                    <!-- Direct Servo Angle & PWM Waveform Controller -->
                    <div class="servo-diag-box">
                        <div class="pwm-badge-row">
                            <span style="font-size:0.8rem; font-weight:bold; color:#e2e8f0;">Rockchip Hardware PWM11 Controller</span>
                            <span class="pwm-chip-tag" id="pwmStatusTag">PWM11: 50.0 Hz (20,000,000 ns)</span>
                        </div>

                        <!-- Mechanical Calibration Section -->
                        <div style="background:#131c31; border:1px solid #1e293b; border-radius:8px; padding:12px; margin-bottom:12px;">
                            <div style="font-size:0.78rem; font-weight:bold; color:#e2e8f0; margin-bottom:6px;">
                                📐 Mechanical Flap Alignment (Set Closed &amp; Divert Positions):
                            </div>
                            <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#94a3b8; margin-bottom:8px;">
                                <span>Resting CLOSED Angle: <b id="cfgClosedTxt" style="color:#22c55e;">0°</b></span>
                                <span>Trash DIVERT Angle: <b id="cfgDivertTxt" style="color:#ef4444;">90°</b></span>
                            </div>
                            <div style="display:flex; gap:8px; flex-wrap:wrap;">
                                <button class="btn-servo-angle" onclick="saveAsClosedAngle()" style="background:#065f46; color:#a7f3d0; border-color:#059669;">
                                    📌 Set Slider as CLOSED
                                </button>
                                <button class="btn-servo-angle" onclick="saveAsDivertAngle()" style="background:#7f1d1d; color:#fca5a5; border-color:#dc2626;">
                                    📌 Set Slider as DIVERT
                                </button>
                                <button class="btn-servo-angle" onclick="invertFlapAngles()" style="background:#1e293b; color:#38bdf8;">
                                    🔄 Swap Closed &amp; Divert
                                </button>
                            </div>
                        </div>

                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                            <span style="font-size:0.8rem; font-weight:600; color:#cbd5e1;">Test Flap Angle</span>
                            <span style="font-size:0.78rem; color:#38bdf8; font-family:monospace;">
                                <b id="servoAngleTxt">0°</b> &bull; <span id="servoPulseTxt">1.000 ms</span> &bull; <span id="servoDutyTxt">1,000,000 ns</span>
                            </span>
                        </div>
                        <input type="range" id="servoAngleSlider" min="0" max="180" step="5" value="0" oninput="onServoSliderChange()">
                        
                        <!-- Standard Angle Presets -->
                        <span class="pulse-subheading">Standard Angle Controls:</span>
                        <div class="servo-btn-bar">
                            <button class="btn-servo-angle" onclick="setServoAngle(0)">0°</button>
                            <button class="btn-servo-angle" onclick="setServoAngle(30)">30°</button>
                            <button class="btn-servo-angle" onclick="setServoAngle(45)">45°</button>
                            <button class="btn-servo-angle" onclick="setServoAngle(60)">60°</button>
                            <button class="btn-servo-angle" onclick="setServoAngle(90)">90°</button>
                            <button class="btn-servo-angle" onclick="setServoAngle(120)">120°</button>
                            <button class="btn-servo-angle" onclick="setServoAngle(135)">135°</button>
                            <button class="btn-servo-angle" onclick="setServoAngle(180)">180°</button>
                            <button class="btn-servo-angle" onclick="runServoSweep()">🔄 Sweep</button>
                        </div>

                        <!-- Direct Pulse Width Calibration -->
                        <span class="pulse-subheading">Direct Pulse Width Calibration (Extended Travel):</span>
                        <div class="servo-btn-bar">
                            <button class="btn-servo-angle" onclick="setServoPulse(0.6)">0.6 ms (Min Limit)</button>
                            <button class="btn-servo-angle" onclick="setServoPulse(1.0)">1.0 ms (0° Rest)</button>
                            <button class="btn-servo-angle" onclick="setServoPulse(1.5)">1.5 ms (90° Center)</button>
                            <button class="btn-servo-angle" onclick="setServoPulse(2.0)">2.0 ms (180° End)</button>
                            <button class="btn-servo-angle" onclick="setServoPulse(2.4)">2.4 ms (Max Limit)</button>
                        </div>

                        <div class="wiring-notice">
                            <strong>⚠️ MG996R Hardware Verification Checklist:</strong><br>
                            1. <b>Orange / Yellow (Signal):</b> Connect to Luckfox Pico <b>Physical Pin 4</b> (PWM11 / GPIO55).<br>
                            2. <b>Red (VCC):</b> Connect to a <b>regulated 5.0V–6.0V external power supply</b> (e.g. 5V adapter).<br>
                            &nbsp;&nbsp;&nbsp;&nbsp;<i>* CRITICAL: Do NOT power the MG996R from the Pico 3.3V pin (it draws up to 1.5A stall)!</i><br>
                            3. <b>Brown / Black (GND):</b> Must connect to <b>BOTH</b> external supply GND <u>AND</u> Luckfox Pico <b>Pin 8 (GND)</b> for common ground.
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Real-Time Camera Stream Refresh
        function refreshCamera() {
            const img = document.getElementById("liveCam");
            const nextImg = new Image();
            nextImg.onload = () => { img.src = nextImg.src; };
            nextImg.src = "/snapshot.bmp?t=" + Date.now();
        }
        setInterval(refreshCamera, 180);

        // Visual Filter Update (CSS White Balance & Contrast tuning)
        function updateCssFilter() {
            const img = document.getElementById("liveCam");
            const contrast = document.getElementById("contrastSlider").value;
            const bright = document.getElementById("brightSlider").value;
            const wb = document.getElementById("wbCheck").checked;

            document.getElementById("contrastVal").innerText = contrast + "%";
            document.getElementById("brightVal").innerText = bright + "%";

            const wbFilter = wb ? "hue-rotate(345deg) saturate(112%)" : "";
            img.style.filter = `contrast(${contrast}%) brightness(${bright}%) ${wbFilter}`;
        }
        updateCssFilter();

        // Hardware Sensor Tuning Handler
        let hwDebounce = null;
        function onHardwareSliderChange() {
            const exp = document.getElementById("expSlider").value;
            const gain = document.getElementById("gainSlider").value;
            const vflip = document.getElementById("vflipCheck").checked ? 1 : 0;
            const hflip = document.getElementById("hflipCheck").checked ? 1 : 0;

            document.getElementById("expVal").innerText = exp;
            document.getElementById("gainVal").innerText = gain;

            clearTimeout(hwDebounce);
            hwDebounce = setTimeout(() => {
                fetch("/api/camera_settings", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ exposure: exp, gain: gain, vflip: vflip, hflip: hflip })
                });
            }, 120);
        }

        // Quick Lighting Presets
        function applyPreset(name) {
            document.querySelectorAll(".btn-preset").forEach(b => b.classList.remove("active"));
            event.target.classList.add("active");

            if (name === "studio") {
                document.getElementById("expSlider").value = 800;
                document.getElementById("gainSlider").value = 2048;
                document.getElementById("contrastSlider").value = 115;
                document.getElementById("brightSlider").value = 105;
            } else if (name === "bright") {
                document.getElementById("expSlider").value = 1100;
                document.getElementById("gainSlider").value = 3072;
                document.getElementById("contrastSlider").value = 120;
                document.getElementById("brightSlider").value = 115;
            } else if (name === "night") {
                document.getElementById("expSlider").value = 1350;
                document.getElementById("gainSlider").value = 5120;
                document.getElementById("contrastSlider").value = 130;
                document.getElementById("brightSlider").value = 125;
            } else if (name === "raw") {
                document.getElementById("expSlider").value = 600;
                document.getElementById("gainSlider").value = 1024;
                document.getElementById("contrastSlider").value = 100;
                document.getElementById("brightSlider").value = 100;
            }
            updateCssFilter();
            onHardwareSliderChange();
        }

        // Real-Time Hardware Telemetry Refresh
        async function fetchTelemetry() {
            try {
                const res = await fetch("/api/live_telemetry");
                if (!res.ok) return;
                const d = await res.json();

                document.getElementById("fpsTag").innerText = d.camera_fps.toFixed(1) + " FPS";
                document.getElementById("coreTemp").innerText = d.core_temp;
                document.getElementById("trashCount").innerText = d.trash_diverted;

                const uDist = d.ultrasonic_distance_cm;
                document.getElementById("ultraDist").innerText = (uDist > 0 ? uDist.toFixed(1) + " cm" : "-- cm");
                document.getElementById("waterDepth").innerText = d.water_depth_cm.toFixed(1) + " cm";

                document.getElementById("waterVolt").innerText = d.water_voltage.toFixed(4) + " V";
                document.getElementById("waterPct").innerText = d.water_percentage.toFixed(1) + "%";
                document.getElementById("waterProgress").style.width = Math.min(100, Math.max(0, d.water_percentage)) + "%";

                const pumpEl = document.getElementById("pumpStatus");
                pumpEl.innerText = d.pump_status;
                pumpEl.className = "metric-value " + (d.pump_status === "ON" ? "text-green" : "text-amber");

                const gateEl = document.getElementById("gateStatus");
                gateEl.innerText = d.gate_status;
                gateEl.className = "metric-value " + (d.gate_status === "DIVERTING" ? "text-red" : "text-green");

                document.getElementById("lcdLine1").innerText = d.lcd_line1;
                document.getElementById("lcdLine2").innerText = d.lcd_line2;

                if (d.servo_angle !== undefined) {
                    const elAng = document.getElementById("servoAngleTxt");
                    if (elAng) elAng.innerText = d.servo_angle + "°";
                    const elPulse = document.getElementById("servoPulseTxt");
                    if (elPulse) elPulse.innerText = d.servo_pulse_ms.toFixed(3) + " ms";
                    const elDuty = document.getElementById("servoDutyTxt");
                    if (elDuty && d.servo_duty_ns) {
                        elDuty.innerText = d.servo_duty_ns.toLocaleString() + " ns";
                    }
                }

                if (d.auto_divert !== undefined) {
                    updateAutoUi(d.auto_divert);
                }

                if (d.closed_angle !== undefined) {
                    currentClosedAngle = d.closed_angle;
                    currentDivertAngle = d.divert_angle;
                    updateFlapLabels();
                }

            } catch (err) {
                console.warn("Telemetry fetch error:", err);
            }
        }
        setInterval(fetchTelemetry, 350);

        let currentClosedAngle = 0;
        let currentDivertAngle = 90;

        function updateFlapLabels() {
            const elC1 = document.getElementById("btnClosedDeg");
            const elD1 = document.getElementById("btnDivertDeg");
            const elC2 = document.getElementById("cfgClosedTxt");
            const elD2 = document.getElementById("cfgDivertTxt");
            if (elC1) elC1.innerText = currentClosedAngle + "°";
            if (elD1) elD1.innerText = currentDivertAngle + "°";
            if (elC2) elC2.innerText = currentClosedAngle + "°";
            if (elD2) elD2.innerText = currentDivertAngle + "°";
        }

        async function forceCloseFlap() {
            setServoAngle(currentClosedAngle);
            try {
                await fetch("/api/force_close", { method: "POST" });
            } catch (e) {
                console.error(e);
            }
        }

        async function saveAsClosedAngle() {
            const angle = parseFloat(document.getElementById("servoAngleSlider").value);
            currentClosedAngle = angle;
            updateFlapLabels();
            await syncFlapConfig();
        }

        async function saveAsDivertAngle() {
            const angle = parseFloat(document.getElementById("servoAngleSlider").value);
            currentDivertAngle = angle;
            updateFlapLabels();
            await syncFlapConfig();
        }

        async function invertFlapAngles() {
            const tmp = currentClosedAngle;
            currentClosedAngle = currentDivertAngle;
            currentDivertAngle = tmp;
            updateFlapLabels();
            forceCloseFlap();
            await syncFlapConfig();
        }

        async function syncFlapConfig() {
            try {
                await fetch("/api/set_flap_angles", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ closed_angle: currentClosedAngle, divert_angle: currentDivertAngle })
                });
            } catch (e) {
                console.error(e);
            }
        }

        function updateAutoUi(isArmed) {
            const badge = document.getElementById("autoModeBadge");
            const btn = document.getElementById("btnToggleAuto");
            if (!badge || !btn) return;
            if (isArmed) {
                badge.innerText = "ARMED (AUTO-DIVERT ON)";
                badge.style.background = "rgba(34, 197, 94, 0.15)";
                badge.style.borderColor = "var(--accent-green)";
                badge.style.color = "var(--accent-green)";
                btn.innerHTML = "🚨 ARMED (Click to Set STANDBY)";
                btn.style.background = "#059669";
            } else {
                badge.innerText = "STANDBY (MANUAL ONLY)";
                badge.style.background = "rgba(245, 158, 11, 0.15)";
                badge.style.borderColor = "var(--accent-amber)";
                badge.style.color = "var(--accent-amber)";
                btn.innerHTML = "⏸️ Mode: STANDBY (Click to ARM Auto-Divert)";
                btn.style.background = "#334155";
            }
        }

        async function toggleAutoDivert() {
            try {
                const res = await fetch("/api/toggle_auto_divert", { method: "POST" });
                const d = await res.json();
                updateAutoUi(d.auto_divert);
            } catch (e) {
                console.error(e);
            }
        }

        async function resetTrashCounter() {
            try {
                await fetch("/api/reset_trash_counter", { method: "POST" });
            } catch (e) {
                console.error(e);
            }
        }

        // Hardware Controls
        async function triggerGate() {
            try {
                await fetch("/api/trigger_gate", { method: "POST" });
            } catch (e) {
                console.error(e);
            }
        }

        async function togglePump() {
            try {
                await fetch("/api/toggle_pump", { method: "POST" });
            } catch (e) {
                console.error(e);
            }
        }

        // Direct Servo Controls
        let servoDebounce = null;
        function onServoSliderChange() {
            const angle = document.getElementById("servoAngleSlider").value;
            document.getElementById("servoAngleTxt").innerText = angle + "°";
            const pulse = 1.0 + (angle / 180.0) * 1.0;
            document.getElementById("servoPulseTxt").innerText = pulse.toFixed(3) + " ms";
            document.getElementById("servoDutyTxt").innerText = Math.round(pulse * 1000000).toLocaleString() + " ns";

            clearTimeout(servoDebounce);
            servoDebounce = setTimeout(() => {
                setServoAngle(angle);
            }, 80);
        }

        async function setServoAngle(angle) {
            document.getElementById("servoAngleSlider").value = angle;
            document.getElementById("servoAngleTxt").innerText = angle + "°";
            const pulse = 1.0 + (angle / 180.0) * 1.0;
            document.getElementById("servoPulseTxt").innerText = pulse.toFixed(3) + " ms";
            document.getElementById("servoDutyTxt").innerText = Math.round(pulse * 1000000).toLocaleString() + " ns";
            try {
                await fetch("/api/set_servo_angle", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ angle: angle })
                });
            } catch (e) {
                console.error(e);
            }
        }

        async function setServoPulse(pulse_ms) {
            const angle = Math.max(0, Math.min(180, (pulse_ms - 1.0) * 180.0));
            document.getElementById("servoAngleSlider").value = angle;
            document.getElementById("servoAngleTxt").innerText = Math.round(angle) + "°";
            document.getElementById("servoPulseTxt").innerText = Number(pulse_ms).toFixed(3) + " ms";
            document.getElementById("servoDutyTxt").innerText = Math.round(pulse_ms * 1000000).toLocaleString() + " ns";
            try {
                await fetch("/api/set_servo_pulse", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ pulse_ms: pulse_ms })
                });
            } catch (e) {
                console.error(e);
            }
        }

        async function runServoSweep() {
            try {
                await fetch("/api/test_servo_sweep", { method: "POST" });
            } catch (e) {
                console.error(e);
            }
        }
    </script>
</body>
</html>
"""


class LiveRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Suppress HTTP access logging

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            body = HTML_DASHBOARD.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        elif path == "/api/live_telemetry":
            with STATE_LOCK:
                data = json.dumps(LIVE_STATE).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
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
                    self.end_headers()
                    self.wfile.write(bmp_bytes)
            except Exception:
                self.send_error(503, "Camera stream unavailable")
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/trigger_gate":
            threading.Thread(target=run_full_diversion_cycle, args=(2.5,), daemon=True).start()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","gate":"pwm_triggered"}')
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
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
            except Exception as e:
                self.send_error(400, f"Error: {e}")
            return

        elif path == "/api/set_servo_pulse":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                data = json.loads(body)
                pulse_ms = float(data.get("pulse_ms", 1.0))
                set_servo_pulse_direct(pulse_ms)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
            except Exception as e:
                self.send_error(400, f"Error: {e}")
            return

        elif path == "/api/test_servo_sweep":
            def _sweep():
                print(">> [SERVO SWEEP] Starting hardware PWM test sweep: 0° -> 45° -> 90° -> 135° -> 180° -> 0°...")
                for ang in [0, 45, 90, 135, 180, 90, 0]:
                    actuate_servo_to_angle(ang)
                    time.sleep(0.5)
                print(">> [SERVO SWEEP] Hardware PWM test sweep complete.")
            threading.Thread(target=_sweep, daemon=True).start()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","sweep":"started"}')
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
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
            except Exception as e:
                self.send_error(400, f"Error: {e}")
            return

        elif path == "/api/toggle_pump":
            try:
                req = urllib.request.Request("http://127.0.0.1:8080/api/toggle_pump", data=b"", method="POST")
                urllib.request.urlopen(req, timeout=1.0)
            except Exception:
                pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","pump":"toggled"}')
            return

        elif path == "/api/toggle_auto_divert":
            with STATE_LOCK:
                LIVE_STATE["auto_divert"] = not LIVE_STATE.get("auto_divert", False)
                cur = LIVE_STATE["auto_divert"]
                closed_ang = LIVE_STATE.get("closed_angle", 0.0)
            if not cur:
                # Switched to Standby: Immediately force flap to CLOSED angle!
                print(f">> [STANDBY ACTIVATED] Forcing flap to CLOSED position ({closed_ang}°)...")
                actuate_servo_to_angle(closed_ang)
                with STATE_LOCK:
                    LIVE_STATE["gate_status"] = "CLOSED"
            print(f">> [AUTO DIVERT MODE] Switched to: {'ARMED (AUTO ON)' if cur else 'STANDBY (MANUAL ONLY)'}")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "auto_divert": cur}).encode("utf-8"))
            return

        elif path == "/api/force_close":
            with STATE_LOCK:
                closed_ang = LIVE_STATE.get("closed_angle", 0.0)
                LIVE_STATE["gate_status"] = "CLOSED"
            print(f">> [FORCE CLOSE] Explicitly moving flap to {closed_ang}° CLOSED position...")
            actuate_servo_to_angle(closed_ang)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","gate":"closed"}')
            return

        elif path == "/api/set_flap_angles":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                data = json.loads(body)
                with STATE_LOCK:
                    if "closed_angle" in data:
                        LIVE_STATE["closed_angle"] = float(data["closed_angle"])
                    if "divert_angle" in data:
                        LIVE_STATE["divert_angle"] = float(data["divert_angle"])
                    c_ang = LIVE_STATE["closed_angle"]
                    d_ang = LIVE_STATE["divert_angle"]
                # Move to new closed angle immediately
                actuate_servo_to_angle(c_ang)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status":"ok","closed_angle":c_ang,"divert_angle":d_ang}).encode("utf-8"))
            except Exception as e:
                self.send_error(400, f"Error: {e}")
            return

        elif path == "/api/reset_trash_counter":
            with STATE_LOCK:
                LIVE_STATE["trash_diverted"] = 0
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","trash_diverted":0}')
            return

        self.send_error(404, "Not Found")


def main():
    print("=" * 65)
    print("  SWACHH-NAYAN: LIVE PRODUCTION DASHBOARD (PORT 8088)")
    print("  Zero-Mock Real-Time Integration with Hardware PWM11 Servo")
    print("=" * 65)

    # 1. Start background hardware polling worker
    t_worker = threading.Thread(target=background_hardware_worker, daemon=True, name="HwWorker")
    t_worker.start()

    # 2. Start HTTP server
    server = ThreadingHTTPServer(("0.0.0.0", PORT), LiveRequestHandler)
    print(f">> Server listening on 0.0.0.0:{PORT}")
    print(f">> Luckfox Pico URL: http://172.32.0.93:{PORT}")
    print(f">> Host Mac URL: http://localhost:{PORT} (via adb forward)")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Live Dashboard Server...")
        server.server_close()


if __name__ == "__main__":
    main()
