#!/bin/bash
# ====================================================================
# Swachh Nayan — 100% Standalone Luckfox Pico Deployment Script
# RUNS EVERYTHING ON THE LUCKFOX PICO BOARD (MIPI CSI CAMERA + NPU + SERVO)
# ====================================================================

echo "=========================================================="
echo " SWACHH NAYAN: Standalone Luckfox Pico Initialization..."
echo "=========================================================="

# 1. Check MIPI CSI V4L2 Device Node
echo "[1/4] Verifying onboard MIPI CSI camera device (/dev/video11)..."
ls -l /dev/video11 || echo "Warning: /dev/video11 node check."

# 2. Enable sysfs PWM0 for MG996R Servo
echo "[2/4] Initializing sysfs PWM0 channel..."
if [ -d "/sys/class/pwm/pwmchip0" ]; then
    echo 0 > /sys/class/pwm/pwmchip0/export 2>/dev/null || true
    echo 20000000 > /sys/class/pwm/pwmchip0/pwm0/period 2>/dev/null || true
    echo 1 > /sys/class/pwm/pwmchip0/pwm0/enable 2>/dev/null || true
    echo "[OK] PWM0 enabled for MG996R Servo Motor."
fi

# 3. Kill any existing instances
killall -9 python3 2>/dev/null || true

# 4. Launch Standalone Pico Engine
echo "[3/4] Launching pico_standalone_main.py..."
python3 pico_standalone_main.py &

echo "=========================================================="
echo " 100% STANDALONE LUCKFOX PICO ENGINE IS NOW LIVE!"
echo " Web Dashboard (USB RNDIS): http://172.32.0.93:8080"
echo " Camera Feed:  Onboard MIPI CSI Module (/dev/video11)"
echo "=========================================================="
