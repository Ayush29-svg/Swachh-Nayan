"""
Swachh Nayan — Hardware & Software Integration Configuration
Board: Luckfox Pico (RV1103 NPU Board)
OS: Linux (Buildroot / Ubuntu)
"""

import os

# ==========================================
# 1. CAMERA & VISION CONFIGURATION
# ==========================================
CAMERA_INDEX = 0             # /dev/video0 (MIPI CSI or USB Camera)
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 30

# Detection Bounding Box Trigger Zone (0.0 to 1.0 relative coordinates)
# When detected plastic enters this horizontal/vertical zone, activate scoop
TRIGGER_ZONE = {
    "xmin": 0.2,
    "xmax": 0.8,
    "ymin": 0.3,
    "ymax": 0.7
}

CONFIDENCE_THRESHOLD = 0.60  # Minimum confidence for plastic detection

# ==========================================
# 2. RKNN NPU MODEL CONFIGURATION
# ==========================================
RKNN_MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "swachh_nayan_rv1103.rknn")
TARGET_PLATFORM = "rv1103"
CLASSES = ["background", "plastic_bottle", "plastic_waste", "leaf", "organic_waste"]

# ==========================================
# 3. SERVO MOTOR (MG996R) CONFIGURATION
# ==========================================
# PWM sysfs path on Luckfox Pico (typically pwmchip0 / pwm0)
PWM_CHIP_PATH = "/sys/class/pwm/pwmchip0"
PWM_CHANNEL = 0
PWM_PERIOD_NS = 20000000     # 50 Hz frequency = 20ms period (20,000,000 ns)

# MG996R Duty Cycles (in nanoseconds)
# 0 degrees (Resting / Submerged in water): ~1.0 ms (1,000,000 ns)
# 120 degrees (Ejection / Dumping to bucket): ~2.2 ms (2,200,000 ns)
SERVO_REST_DUTY_NS = 1000000   # 0 degrees (In-water scoop position)
SERVO_DUMP_DUTY_NS = 2200000   # 120 degrees (Over-the-rim dumping position)
SCOOP_HOLD_TIME_SEC = 1.5      # Time to hold dump position for trash to fall

# GPIO Fallback pin if hardware PWM is disabled (e.g. GPIO1_C0 / GPIO pin 56)
SERVO_GPIO_PIN = 56

# ==========================================
# 4. LCD DISPLAY (16x2 I2C) CONFIGURATION
# ==========================================
I2C_BUS = 1                  # /dev/i2c-1 on Luckfox Pico
I2C_LCD_ADDR = 0x27          # Default PCF8574 I2C address (or 0x3F)

# ==========================================
# 5. ULTRASONIC WATER LEVEL SENSOR (HC-SR04)
# ==========================================
GPIO_TRIG_PIN = 57           # GPIO Pin for Trigger
GPIO_ECHO_PIN = 58           # GPIO Pin for Echo
CRITICAL_WATER_LEVEL_CM = 15 # Water overflow threshold

# ==========================================
# 6. RELAY / PUMP CONTROL
# ==========================================
GPIO_PUMP_RELAY_PIN = 59     # GPIO pin controlling 12V mini pump relay
