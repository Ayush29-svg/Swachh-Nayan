# Swachh-Nayan ESP32-S3 Firmware

Modular Arduino firmware for the **Swachh-Nayan Smart Drain Monitoring** project running on the **Dual Type-C ESP32-S3-CAM (N16R8)** board with an **OV2640 (2MP)** camera module and onboard MicroSD card slot.

Open `SwachhNayan.ino` in Arduino IDE or build with `arduino-cli`.

---

## 1. Hardware & Carrier Pin Map

The board identified is the **Generic Dual Type-C ESP32-S3-CAM (N16R8)** featuring 16MB Flash, 8MB Octal PSRAM, an onboard TF/MicroSD slot, and an OV2640 camera header.

### ⚠️ Pin Conflict Audit & Remapped Connections
On this carrier board, **GPIO 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17, 18** are hardwired to the camera interface, and **GPIO 38, 39, 40** are wired to the onboard TF slot. Connecting external sensors to GPIO 5, 6, 8, or 9 causes bus contention with the camera.

The external peripherals have therefore been assigned to clean, dedicated header pins:

| Peripheral | Board Pin | Function & Notes |
|---|---|---|
| **HC-SR04 TRIG** | **GPIO 41** | Safe general-purpose output |
| **HC-SR04 ECHO** | **GPIO 42** | Input from HC-SR04 (use 1kΩ / 2kΩ voltage divider to step 5V down to 3.3V) |
| **I²C SDA** | **GPIO 1** | Shared I²C Data line for ADS1115 (`0x48`) and 16×2 LCD (`0x27`) |
| **I²C SCL** | **GPIO 2** | Shared I²C Clock line for ADS1115 (`0x48`) and 16×2 LCD (`0x27`) |
| **Servo Actuator** | **GPIO 21** | PWM signal output (Gated by `SERVO_ENABLED`; requires external 5V supply) |
| **MicroSD Card** | **GPIO 38 (CMD), 39 (CLK), 40 (D0)** | Internal onboard TF socket running in high-speed 1-bit `SD_MMC` mode |
| **OV2640 Camera** | Dedicated internal DVP bus | 320×240 (QVGA) hardware JPEG capture with frame buffers in PSRAM |

> [!CAUTION]
> Always power the servo from an external regulated 5V power supply with a common ground to the ESP32. Never draw motor power from the ESP32 3.3V or 5V rails.

---

## 2. MicroSD Card Capabilities

The integrated `SDCardManager` automatically initializes the onboard TF slot on boot without blocking the main loop:
- **Alert Snapshots**: Automatically captures and saves full-resolution JPEG frames to `/captures/<STATE>_<TIMESTAMP>.jpg` whenever a `WASTE_DETECTED` or `POSSIBLE_OBSTRUCTION` event occurs.
- **Telemetry CSV Logging**: Periodically appends real-time sensor metrics (distance, water state, ADC raw, decision state, confidence) to `/telemetry.csv`.
- **Manual Snapshot**: Type `snap` in the Serial Monitor to take an on-demand picture and save it to the card.
- **Storage Reporting**: Free space and file counts are served live to the Web Dashboard.

---

## 3. Web Dashboard & Camera Viewfinder

The responsive local dashboard is served directly by the ESP32 web server at port `80` and is available at:
```
http://<ESP32_IP_ADDRESS>/
```
*(Or locally at `http://localhost:8080/` in simulated demo mode).*

### Features:
- **Live Optical Viewfinder**: Fetches and renders live hardware camera snapshots via `/api/camera/snapshot`.
- **Real-time Telemetry Cards**: Distance, water moisture status, raw ADC, camera health, and AI classification.
- **MicroSD Card Status**: Real-time card presence, total storage, free space in GB, and snapshot count.
- **Distance History Chart**: Dynamic SVG visualizer showing recent ultrasonic readings and depth trends.
- **System Health**: Controller state, heap memory, Wi-Fi RSSI signal strength, and uptime.

---

## 4. Serial Commands (115200 Baud)

Open the Serial Monitor at 115200 baud to issue live diagnostic commands:
- `help` : Lists all available commands.
- `status` : Displays a one-line summary of all sensor, camera, servo, and SD readings.
- `sd` : Prints SD card mount status, capacity, and total snapshots stored.
- `snap` : Manually captures a frame from the OV2640 and saves it to the SD card.
- `calibrate dry` : Captures current moisture sensor reading as the dry baseline.
- `calibrate wet` : Captures current moisture sensor reading as the wet baseline.
- `manual divert` : Requests a test divert action (safe testing).
- `manual safe` : Returns servo to safe position.
- `selftest` : Executes assertion test suite on decision engine states (mock mode).

---

## 5. Build and Flash

### CLI Compilation:
```bash
arduino-cli compile --fqbn esp32:esp32:esp32s3 firmware/SwachhNayan
```

### Arduino IDE Settings:
- **Board**: `ESP32S3 Dev Module`
- **USB CDC On Boot**: `Enabled`
- **CPU Frequency**: `240MHz (WiFi)`
- **PSRAM**: `OPI PSRAM` (Required for camera frame buffers)
- **Flash Size**: `16MB (128Mb)`
- **Partition Scheme**: `16MB with SPIFFS/FATFS` (or `Huge APP`)
