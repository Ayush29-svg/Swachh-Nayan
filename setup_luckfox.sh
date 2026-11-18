#!/bin/bash
# ====================================================================
# Swachh Nayan — Luckfox Pico (RV1103 NPU Board) Deployment Setup Script
# Configures Linux sysfs PWM, I2C, GPIO overlays, and Python environment
# ====================================================================

echo "========================================================"
echo " SWACHH NAYAN: Luckfox Pico RV1103 System Initialization"
echo "========================================================"

# 1. Update package manager & install dependencies
echo "[1/5] Installing System Dependencies & Python Libraries..."
apt-get update -y || true
apt-get install -y python3-pip python3-opencv python3-smbus i2c-tools || true
pip3 install rknnlite-api opencv-python smbus2 numpy

# 2. Enable I2C and PWM Overlays in sysfs
echo "[2/5] Configuring Hardware Sysfs Overlays..."
modprobe i2c-dev || true

# Export PWM0 if available
if [ -d "/sys/class/pwm/pwmchip0" ]; then
    echo 0 > /sys/class/pwm/pwmchip0/export 2>/dev/null || true
    echo 20000000 > /sys/class/pwm/pwmchip0/pwm0/period 2>/dev/null || true
    echo 1 > /sys/class/pwm/pwmchip0/pwm0/enable 2>/dev/null || true
    echo "[OK] Sysfs PWM Channel 0 Enabled (50Hz / 20ms)."
fi

# Export GPIOs for Sensors & Relay
echo "[3/5] Exporting GPIO Pins..."
for pin in 56 57 58 59; do
    echo $pin > /sys/class/gpio/export 2>/dev/null || true
done

# 4. Check I2C LCD Connection
echo "[4/5] Scanning I2C Bus for 16x2 LCD..."
i2cdetect -y 1 || echo "i2cdetect tool not available."

# 5. Create Systemd Service for Auto-Start on Boot
echo "[5/5] Creating Systemd Auto-Start Service..."
cat <<EOF > /etc/systemd/system/swachh_nayan.service
[Unit]
Description=Swachh Nayan AI Storm-Drain Trash Diverter Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /root/Swachh_Nayan/main_controller.py
WorkingDirectory=/root/Swachh_Nayan
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable swachh_nayan.service

echo "========================================================"
echo " SWACHH NAYAN DEPLOYMENT COMPLETE!                      "
echo " To run live controller: python3 main_controller.py     "
echo " To test peripherals:     python3 test_hardware.py      "
echo "========================================================"
