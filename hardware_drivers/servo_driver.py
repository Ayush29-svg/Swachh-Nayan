"""
Swachh Nayan — MG996R Servo Motor Hardware Driver
Supports Linux PWM (sysfs) on Luckfox Pico (RV1103) & Software GPIO Fallback
"""

import os
import time
import sys

# Add parent dir to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class MG996RServoDriver:
    def __init__(self):
        self.use_sysfs_pwm = False
        self.pwm_channel_path = os.path.join(config.PWM_CHIP_PATH, f"pwm{config.PWM_CHANNEL}")
        
        self._init_pwm()

    def _init_pwm(self):
        """Export and configure PWM via sysfs if available."""
        try:
            if not os.path.exists(config.PWM_CHIP_PATH):
                print(f"[SERVO] Warning: PWM chip {config.PWM_CHIP_PATH} not found. Operating in simulation mode.")
                return

            # Export PWM channel if not exported
            export_path = os.path.join(config.PWM_CHIP_PATH, "export")
            if not os.path.exists(self.pwm_channel_path):
                with open(export_path, "w") as f:
                    f.write(str(config.PWM_CHANNEL))
                time.sleep(0.1)

            # Set period (50 Hz = 20,000,000 ns)
            period_path = os.path.join(self.pwm_channel_path, "period")
            with open(period_path, "w") as f:
                f.write(str(config.PWM_PERIOD_NS))

            # Enable PWM
            enable_path = os.path.join(self.pwm_channel_path, "enable")
            with open(enable_path, "w") as f:
                f.write("1")

            self.use_sysfs_pwm = True
            print(f"[SERVO] Linux sysfs PWM successfully initialized on {self.pwm_channel_path}")

        except Exception as e:
            print(f"[SERVO] Could not initialize sysfs PWM: {e}. Falling back to simulation.")
            self.use_sysfs_pwm = False

    def _set_duty_ns(self, duty_ns):
        """Set PWM duty cycle in nanoseconds."""
        if self.use_sysfs_pwm:
            try:
                duty_path = os.path.join(self.pwm_channel_path, "duty_cycle")
                with open(duty_path, "w") as f:
                    f.write(str(duty_ns))
            except Exception as e:
                print(f"[SERVO Error] Failed to write duty_cycle: {e}")
        else:
            # Simulation / Log output
            angle = 0 if duty_ns == config.SERVO_REST_DUTY_NS else 120
            print(f"[SERVO SIM] Set position: {angle}° (Duty: {duty_ns} ns)")

    def move_to_rest(self):
        """Move mesh scoop to resting position (0° submerged in water flow)."""
        print("[SERVO] Moving scoop to RESTING position (0° submerged)...")
        self._set_duty_ns(config.SERVO_REST_DUTY_NS)

    def move_to_dump(self):
        """Move mesh scoop to ejection position (120° dumping trash over rim)."""
        print("[SERVO] Moving scoop to DUMPING position (120° over-the-rim)...")
        self._set_duty_ns(config.SERVO_DUMP_DUTY_NS)

    def trigger_scoop_cycle(self):
        """Perform full scoop cycle: Rest -> Dump -> Hold 1.5s -> Rest."""
        print("[SERVO] *** TRASH DETECTED! INITIATING SCOOP CYCLE ***")
        self.move_to_dump()
        time.sleep(config.SCOOP_HOLD_TIME_SEC)
        self.move_to_rest()
        print("[SERVO] Scoop cycle complete. Ready for next detection.")

    def cleanup(self):
        """Disable PWM on exit."""
        if self.use_sysfs_pwm:
            try:
                enable_path = os.path.join(self.pwm_channel_path, "enable")
                with open(enable_path, "w") as f:
                    f.write("0")
                print("[SERVO] PWM disabled.")
            except Exception as e:
                print(f"[SERVO] Cleanup error: {e}")


if __name__ == "__main__":
    print("Testing MG996R Servo Driver...")
    servo = MG996RServoDriver()
    servo.move_to_rest()
    time.sleep(1)
    servo.trigger_scoop_cycle()
    servo.cleanup()
