"""
Swachh Nayan — HC-SR04 Ultrasonic Distance / Water Level Sensor Driver
Board: Luckfox Pico (RV1103) via Linux sysfs GPIO
"""

import time
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class HCSR04SensorDriver:
    def __init__(self, trig_pin=config.GPIO_TRIG_PIN, echo_pin=config.GPIO_ECHO_PIN):
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        self.sysfs_available = False

        self._init_gpio()

    def _init_gpio(self):
        """Export GPIOs via /sys/class/gpio if running on Linux."""
        try:
            if not os.path.exists("/sys/class/gpio"):
                print("[HC-SR04] sysfs GPIO not found. Simulation mode enabled.")
                return

            for pin, direction in [(self.trig_pin, "out"), (self.echo_pin, "in")]:
                pin_dir = f"/sys/class/gpio/gpio{pin}"
                if not os.path.exists(pin_dir):
                    with open("/sys/class/gpio/export", "w") as f:
                        f.write(str(pin))
                    time.sleep(0.05)
                with open(f"{pin_dir}/direction", "w") as f:
                    f.write(direction)

            self.sysfs_available = True
            print(f"[HC-SR04] GPIO initialized: TRIG={self.trig_pin}, ECHO={self.echo_pin}")
        except Exception as e:
            print(f"[HC-SR04] GPIO setup warning: {e}. Running in simulation mode.")

    def measure_distance_cm(self):
        """Measure distance from sensor head to water surface in cm."""
        if not self.sysfs_available:
            return 12.5  # Normal simulated water height distance

        try:
            trig_val_path = f"/sys/class/gpio/gpio{self.trig_pin}/value"
            echo_val_path = f"/sys/class/gpio/gpio{self.echo_pin}/value"

            # Trigger 10us pulse
            with open(trig_val_path, "w") as f:
                f.write("1")
            time.sleep(0.00001)
            with open(trig_val_path, "w") as f:
                f.write("0")

            start_time = time.time()
            stop_time = time.time()

            # Wait for Echo High
            timeout = start_time + 0.04
            with open(echo_val_path, "r") as f:
                while f.read().strip() == "0":
                    start_time = time.time()
                    if start_time > timeout:
                        return 999.0
                    f.seek(0)

            # Wait for Echo Low
            with open(echo_val_path, "r") as f:
                while f.read().strip() == "1":
                    stop_time = time.time()
                    if stop_time > timeout:
                        return 999.0
                    f.seek(0)

            elapsed = stop_time - start_time
            distance_cm = (elapsed * 34300) / 2.0
            return round(distance_cm, 1)

        except Exception as e:
            print(f"[HC-SR04 Error]: {e}")
            return 12.5


if __name__ == "__main__":
    sensor = HCSR04SensorDriver()
    dist = sensor.measure_distance_cm()
    print(f"Measured Water Distance: {dist} cm")
