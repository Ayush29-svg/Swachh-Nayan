# Swachh-Nayan: ESP32-S3-CAM Master Project Package (Updated)

This package contains the complete, tested, and resolved code for **Swachh-Nayan**, including the fixed ESP32-S3 firmware, real-time frontend dashboard, and laptop AI vision server.

---

## 1. What Has Been Fixed

1. **Ultrasonic Sensor Object Detection (`sensor_ultrasonic.cpp` & `.h`)**:
   - Fixed missed echo drops by implementing a 3-cycle glitch tolerance.
   - Added rolling median filtering to remove water reflection noise so objects in the drain are reliably detected.
2. **Decision Engine Logic (`decision_engine.cpp`)**:
   - Removed the blocking dependency on the ADS1115 water sensor so the system no longer crashes into `SENSOR_FAULT`.
   - Enabled smooth confirmation of waste and obstructions within 20 cm.
3. **Camera Driver Stability (`camera_board_config.h` & `camera_manager.cpp`)**:
   - Configured clock frequency to 10MHz safe mode for the OV3660/OV2640 sensor.
   - Allocated double-frame buffers in PSRAM with `CAMERA_GRAB_LATEST` to eliminate NULL frame errors.
4. **Physical 16x2 LCD Display (`display_manager.cpp`)**:
   - Dual address support (`0x27` and `0x3F`) for PCF8574 I2C backpacks.
   - Initialized on clean conflict-free pins: `SDA = GPIO 1`, `SCL = GPIO 2`.
5. **Real-Time Frontend Dashboard (`dashboard/index.html`)**:
   - Increased camera viewport refresh rate from a 6-second lag down to **250ms (live stream)**.
   - Increased telemetry polling to **200ms** for real-time tracking.
   - Added dynamic AI bounding box rendering and live actuation controls.
6. **Laptop Master AI Hub (`swachh_nayan_live_server.py`)**:
   - Automatically connects to ESP32 on **COM5**.
   - Runs `best.onnx` (YOLOv5) in real-time on live camera frames via OpenCV.

---

## 2. Quick Start Guide

### Step 1: Flash the ESP32-S3 Firmware
1. Open Arduino IDE.
2. Open `firmware/SwachhNayan/SwachhNayan.ino`.
3. In **Tools**, set:
   - **Board**: `ESP32S3 Dev Module`
   - **USB CDC On Boot**: `Enabled`
   - **Flash Size**: `16MB (128Mb)`
   - **PSRAM**: `OPI PSRAM` (Essential for N16R8)
   - **Port**: Select your port (e.g. `COM5`)
4. Click **Upload**.

### Step 2: Physical Hardware Checks
- **16x2 LCD Contrast**: If the screen glows blue without text, rotate the blue screw on the back of the I2C backpack until characters are sharp.
- **Wiring Pinout**:
  - `HC-SR04 TRIG`: **GPIO 41**
  - `HC-SR04 ECHO`: **GPIO 42** (via 1k/2k divider)
  - `I2C LCD & ADS1115 SDA`: **GPIO 1**
  - `I2C LCD & ADS1115 SCL`: **GPIO 2**
  - `MG996R Servo Signal`: **GPIO 21** (External 5V supply)
  - `Relay Module`: **GPIO 4**

### Step 3: Launch the Live Dashboard on Laptop
1. Double-click `START_SWACHH_NAYAN_STUDIO.bat`.
2. Open your browser at `http://localhost:8088/`.
