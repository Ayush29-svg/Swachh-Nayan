# Swachh Nayan (स्वच्छ नयन)
### AI-Powered Storm-Drain Trash Sorting & Automatic Diversion System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Edge AI](https://img.shields.io/badge/AI-YOLOv5%20%7C%20Edge%20Impulse-blue.svg)](https://github.com/)
[![Platforms](https://img.shields.io/badge/Platforms-ESP32--S3%20%7C%20Luckfox%20Pico%20RV1103-brightgreen.svg)](https://github.com/)

---

## 🌊 Overview

**Swachh Nayan** is an intelligent embedded stormwater drain monitoring and debris diversion system designed to prevent plastic waste and municipal floating debris from choking urban drain networks and polluting water bodies.

Using onboard computer vision and Edge AI, Swachh Nayan detects floating waste in real time, displays live telemetry on an interactive web dashboard and physical LCD, and actuates a diversion flapper gate powered by high-torque servos to channel trash into collection bins before it enters main waterways.

---

## 🌟 Key Features

- **Real-Time Visual AI Detection**: Runs quantized lightweight object detection models (YOLOv5n / MobileNet) on edge hardware.
- **Dual Embedded Architecture Support**:
  - **ESP32-S3-CAM (N16R8)**: Modular, production-ready Arduino C++ firmware with integrated Wi-Fi AP/station mode, web server, camera capture, and peripheral control.
  - **Luckfox Pico (RV1103 NPU)**: Linux Buildroot implementation utilizing the onboard 0.5 TOPS NPU (`/dev/rknpu`) and MIPI CSI SC3336 camera module.
- **Automated Actuation & Drainage Protection**:
  - Servo-driven flapper gate (MG996R) for sorting floating debris.
  - Relay control for 12V DC water pump / emergency drainage clearing.
  - Ultrasonic (HC-SR04) and analog water-level monitoring to prevent overflow.
- **Dual Visual Feedback**:
  - **16x2 I2C Character LCD**: Instant physical display of system status, detected objects, and water depth.
  - **Real-Time Studio Web Dashboard**: Clean dark-mode industrial UI with live camera viewport, AI detection HUD banner, manual overrides, and hardware telemetry.

---

## 📁 Repository Structure

```text
Swachh_Nayan/
├── SwachhNayan_ESP32S3_Updated/   # Production modular ESP32-S3 firmware
│   ├── firmware/SwachhNayan/      # Arduino C++ implementation
│   │   ├── SwachhNayan.ino        # Main entrypoint
│   │   ├── camera_manager.cpp     # OV2640 / OV3660 camera driver
│   │   ├── actuator_manager.cpp   # MG996R servo and relay driver
│   │   ├── display_manager.cpp    # 16x2 LCD (I2C) manager
│   │   ├── web_dashboard.cpp      # Async web server & REST endpoints
│   │   └── dashboard/index.html   # Web Studio dashboard UI
│   └── training_pipeline/         # Edge AI ONNX models and labels
├── hardware_drivers/              # Standalone Python hardware drivers
│   ├── servo_driver.py            # Hardware PWM & bit-bang driver
│   ├── relay_driver.py            # Optocoupler relay controller
│   ├── lcd_driver.py              # I2C PCF8574 LCD controller
│   └── ultrasonic_driver.py       # HC-SR04 distance measurement
├── server_live_final.py           # Luckfox Pico Python live master server
├── studio_dashboard.html          # Web Studio UI dashboard
├── training_pipeline/             # Model training & optimization scripts
├── docs/ & schematics             # Assembly guides, architecture blueprints
└── config.py                      # Global configuration parameters
```

---

## 🛠️ Hardware Requirements

| Component | Specification | Purpose |
|---|---|---|
| **Main Controller (Option 1)** | ESP32-S3-CAM (N16R8) | 16MB Flash, 8MB PSRAM, Wi-Fi & BLE |
| **Main Controller (Option 2)** | Waveshare Luckfox Pico RV1103 | ARM Cortex-A7 + RISC-V + 0.5T NPU |
| **Camera Sensor** | OV2640 (ESP32-S3) / SC3336 3MP MIPI CSI (Pico) | Video stream for trash classification |
| **Diverter Servo** | MG996R Metal Gear Servo | Flapper gate rotation (0° to 90°/180°) |
| **Water Pump & Relay** | 12V Mini DC Water Pump + 5V Optocoupler Relay | Water circulation & drainage assist |
| **Display** | 16x2 Character LCD with I2C Backpack (PCF8574) | Physical status display |
| **Level Sensor** | HC-SR04 Ultrasonic / Water level sensor | Depth and overflow monitoring |
| **Power Supply** | LM2596 Buck Converter (12V to 5V 3A DC) | High-current actuator & board power |

---

## 🚀 Getting Started

### Option A: Flashing the ESP32-S3 Firmware
1. Open the Arduino IDE.
2. Install the **ESP32 board package** (Espressif Systems, version 2.0.x or 3.x).
3. Select board: **ESP32S3 Dev Module**.
   - **PSRAM**: `OPI PSRAM` (Enabled)
   - **Flash Size**: `16MB (128Mb)`
   - **Partition Scheme**: `16M Flash (3MB APP / 9.9MB FATFS)` or `Huge APP`
4. Open `SwachhNayan_ESP32S3_Updated/firmware/SwachhNayan/SwachhNayan.ino`.
5. Connect your ESP32-S3 board via USB-C and click **Upload**.
6. Connect to the Wi-Fi AP or view your assigned IP in Serial Monitor to open the Web Studio.

### Option B: Running on Luckfox Pico (Linux)
1. Copy the project files to the Pico:
   ```bash
   scp -r * root@<PICO_IP>:/userdata/swachh_nayan_v2/
   ```
2. Start the master server:
   ```bash
   python3 -u /userdata/swachh_nayan_v2/server_live.py
   ```
3. Open `http://<PICO_IP>:8088/` in any browser to access the live dashboard.

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).
