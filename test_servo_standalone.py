#!/usr/bin/env python3
"""
MG996R Physical Servo Motion Sweep Test for Swachh-Nayan
Runs 7 distinct angle steps on Pin 4 (Hardware PWM11 / GPIO 55)
"""

import os
import sys
import time

PWM_CHIP = "/sys/class/pwm/pwmchip11"
PWM_NODE = "/sys/class/pwm/pwmchip11/pwm0"

print("=" * 60)
print(" SWACHH-NAYAN: PHYSICAL SERVO MOTION TEST")
print(" Pin: Luckfox Pico Physical Pin 4 (PWM11 / GPIO 55)")
print(" Voltage Reminder: MG996R requires 4.8V-6.6V (via 5V buck converter)")
print(" Common GND Reminder: 12V/5V power GND must be linked to Luckfox GND")
print("=" * 60)

# Unexport gpio55 if exported so pinmux enables PWM11
if os.path.exists("/sys/class/gpio/gpio55"):
    os.system("echo 55 > /sys/class/gpio/unexport 2>/dev/null")
    time.sleep(0.05)

# Ensure pwm0 is exported
if not os.path.exists(PWM_NODE):
    if os.path.exists(f"{PWM_CHIP}/export"):
        try:
            with open(f"{PWM_CHIP}/export", "w") as f:
                f.write("0\n")
            time.sleep(0.05)
        except Exception as e:
            pass

# Read current period
try:
    with open(f"{PWM_NODE}/period", "r") as f:
        cur_p = int(f.read().strip())
except Exception:
    cur_p = 0

# Set 50Hz = 20,000,000 ns if not set
if cur_p != 20000000:
    try:
        with open(f"{PWM_NODE}/enable", "w") as f:
            f.write("0\n")
    except Exception:
        pass
    try:
        with open(f"{PWM_NODE}/period", "w") as f:
            f.write("20000000\n")
    except Exception as e:
        print(f"Warning setting period: {e}")

# Ensure duty cycle initialized and enabled
try:
    with open(f"{PWM_NODE}/duty_cycle", "w") as f:
        f.write("1000000\n")
    with open(f"{PWM_NODE}/enable", "w") as f:
        f.write("1\n")
    print("[+] Hardware PWM11 active at 50 Hz (20ms period).")
except Exception as e:
    print(f"[-] Error enabling PWM: {e}")

def set_angle(angle_deg, duty_ns):
    print(f">> Actuating Servo: {angle_deg:3d}° | Duty: {duty_ns} ns ({duty_ns/1000000.0:.2f} ms)...")
    try:
        with open(f"{PWM_NODE}/duty_cycle", "w") as f:
            f.write(f"{duty_ns}\n")
    except Exception as e:
        print(f"[-] Write error: {e}")

# Sweep sequence: 0° -> 45° -> 90° -> 135° -> 180° -> 90° -> 0°
sweep_steps = [
    (0,   1000000), # 1.0 ms (Resting normal flow)
    (45,  1250000), # 1.25 ms
    (90,  1500000), # 1.50 ms (Diverter flapper open)
    (135, 1750000), # 1.75 ms
    (180, 2000000), # 2.00 ms (Max deflection)
    (90,  1500000), # Return through 90
    (0,   1000000), # Return to 0
]

print("\n>>> EXECUTING PHYSICAL SERVO ROTATION SEQUENCE <<<")
for ang, duty in sweep_steps:
    set_angle(ang, duty)
    time.sleep(1.8)

print("\n[+] Servo motion test finished.")
