"""
Swachh Nayan — 5V Optocoupler Relay Driver (12V Water Pump Switch)
Board: Luckfox Pico (RV1103) via Linux sysfs GPIO
"""

import time
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class PumpRelayDriver:
    def __init__(self, pin=config.GPIO_PUMP_RELAY_PIN):
        self.pin = pin
        self.sysfs_available = False
        self.is_pump_on = False

        self._init_gpio()

    def _init_gpio(self):
        try:
            if not os.path.exists("/sys/class/gpio"):
                print("[PUMP RELAY] sysfs GPIO not found. Simulation mode enabled.")
                return

            pin_dir = f"/sys/class/gpio/gpio{self.pin}"
            if not os.path.exists(pin_dir):
                with open("/sys/class/gpio/export", "w") as f:
                    f.write(str(self.pin))
                time.sleep(0.05)

            with open(f"{pin_dir}/direction", "w") as f:
                f.write("out")

            self.sysfs_available = True
            print(f"[PUMP RELAY] GPIO initialized on pin {self.pin}")
        except Exception as e:
            print(f"[PUMP RELAY] GPIO setup warning: {e}. Running in simulation mode.")

    def set_pump(self, state_on=True):
        self.is_pump_on = state_on
        val_str = "1" if state_on else "0"
        
        if self.sysfs_available:
            try:
                val_path = f"/sys/class/gpio/gpio{self.pin}/value"
                with open(val_path, "w") as f:
                    f.write(val_str)
                print(f"[PUMP RELAY] Pump state set to: {'ON' if state_on else 'OFF'}")
            except Exception as e:
                print(f"[PUMP RELAY Error]: {e}")
        else:
            print(f"[PUMP RELAY SIM] Pump state: {'ON' if state_on else 'OFF'}")

    def turn_on(self):
        self.set_pump(True)

    def turn_off(self):
        self.set_pump(False)


if __name__ == "__main__":
    relay = PumpRelayDriver()
    relay.turn_on()
    time.sleep(2)
    relay.turn_off()
