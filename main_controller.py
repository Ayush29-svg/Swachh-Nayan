"""
Swachh Nayan — Master Software & Hardware Integration Controller
Integrates:
- Edge AI Vision (Luckfox Pico NPU / OpenCV)
- MG996R Servo Overhead Mesh Scoop Lifter
- 16x2 I2C LCD Real-Time Status Display
- HC-SR04 Water Level / Overflow Protection
- 12V Mini Submersible Water Pump Relay
"""

import cv2
import time
import os
import sys

import config
from hardware_drivers.servo_driver import MG996RServoDriver
from hardware_drivers.lcd_driver import LCD1602I2CDriver
from hardware_drivers.ultrasonic_driver import HCSR04SensorDriver
from hardware_drivers.relay_driver import PumpRelayDriver
from ai_inference.rknn_detector import RKNNNPUWasteDetector


class SwachhNayanController:
    def __init__(self, camera_idx=config.CAMERA_INDEX):
        print("==================================================")
        print(" SWACHH NAYAN: AI STORM-DRAIN TRASH DIVERTER SYSTEM")
        print(" Initializing Hardware & Software Integration...   ")
        print("==================================================")

        # 1. Initialize Hardware Drivers
        self.servo = MG996RServoDriver()
        self.lcd = LCD1602I2CDriver()
        self.water_sensor = HCSR04SensorDriver()
        self.pump_relay = PumpRelayDriver()

        # 2. Initialize AI Vision Engine
        self.detector = RKNNNPUWasteDetector()

        # 3. System State Variables
        self.trash_count = 0
        self.camera_idx = camera_idx
        self.cap = None
        self.is_running = False
        self.cooldown_active = False
        self.last_scoop_time = 0
        self.cooldown_sec = 3.0  # Cooldown period after a scoop cycle

        # Move servo to resting position & turn pump on
        self.servo.move_to_rest()
        self.pump_relay.turn_on()
        self.lcd.update_status(self.trash_count, "SYSTEM ACTIVE")

    def init_camera(self):
        """Open video capture stream."""
        print(f"[CAM] Opening camera index {self.camera_idx}...")
        self.cap = cv2.VideoCapture(self.camera_idx)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

        if not self.cap.isOpened():
            print(f"[CAM Error] Unable to open camera {self.camera_idx}. Check cable/index.")
            return False
        
        print("[CAM] Camera feed online (640x480 @ 30fps).")
        return True

    def run_main_loop(self):
        """Master event-driven hardware-software control loop."""
        if not self.init_camera():
            print("[SYSTEM] Camera failed. Running headless hardware test mode...")
            self._headless_mode()
            return

        self.is_running = True
        print("\n>>> SWACHH NAYAN SYSTEM IS LIVE! PRESS 'q' TO QUIT <<<\n")

        try:
            while self.is_running:
                ret, frame = self.cap.read()
                if not ret:
                    print("[CAM Error] Failed to grab frame.")
                    time.sleep(0.1)
                    continue

                curr_time = time.time()

                # Check Cooldown State
                if self.cooldown_active and (curr_time - self.last_scoop_time > self.cooldown_sec):
                    self.cooldown_active = False
                    self.lcd.update_status(self.trash_count, "SYSTEM ACTIVE")

                # 1. Measure Water Level & Overflow Protection
                water_dist = self.water_sensor.measure_distance_cm()
                if water_dist < config.CRITICAL_WATER_LEVEL_CM:
                    # Water level too high / danger of overflow!
                    self.lcd.display_line(2, "WARN: WATER HIGH")

                # 2. Run AI Inference on Camera Frame
                annotated_frame, detections = self.detector.detect_waste(frame)

                # 3. Process Detections & Evaluate Scoop Trigger
                trigger_scoop = False
                for det in detections:
                    if det["in_trigger_zone"] and not self.cooldown_active:
                        trigger_scoop = True
                        print(f"[EVENT] Plastic detected in trigger zone! Confidence: {det['confidence']*100:.1f}%")
                        break

                # 4. Actuate Hardware Scoop if Triggered
                if trigger_scoop:
                    self.trash_count += 1
                    self.cooldown_active = True
                    self.last_scoop_time = time.time()

                    # Update LCD to show scooping action
                    self.lcd.update_status(self.trash_count, "TRASH SCOOPING!")

                    # Execute Servo Scoop Cycle (Rest -> 120° Dump -> Hold 1.5s -> Rest)
                    self.servo.trigger_scoop_cycle()

                    # Reset LCD to Active
                    self.lcd.update_status(self.trash_count, "SCOOP COMPLETE")

                # 5. Overlay Live Status Info on Frame
                cv2.putText(annotated_frame, f"TRASH CT: {self.trash_count}", (20, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                cv2.putText(annotated_frame, f"PUMP: {'ON' if self.pump_relay.is_pump_on else 'OFF'}", (20, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # Display GUI Frame if desktop display available
                try:
                    cv2.imshow("Swachh Nayan — Live AI Trash Monitor", annotated_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        self.is_running = False
                except Exception:
                    # Running headless on Linux CLI
                    pass

        except KeyboardInterrupt:
            print("\n[SYSTEM] Keyboard Interrupt received. Shutting down gracefully...")

        finally:
            self.shutdown()

    def _headless_mode(self):
        """Fall-back loop for headless testing without camera."""
        print("[HEADLESS] Simulating hardware integration loop...")
        for i in range(3):
            print(f"[HEADLESS] Cycle {i+1}: Simulating detection...")
            self.trash_count += 1
            self.lcd.update_status(self.trash_count, "SIM SCOOPING")
            self.servo.trigger_scoop_cycle()
            time.sleep(1)
        self.shutdown()

    def shutdown(self):
        """Safe hardware teardown on shutdown."""
        print("\n==================================================")
        print(" Safely Shutting Down Hardware Drivers...         ")
        print("==================================================")
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()

        self.pump_relay.turn_off()
        self.servo.move_to_rest()
        self.servo.cleanup()
        self.detector.release()
        self.lcd.update_status(self.trash_count, "SYSTEM SHUTDOWN")
        print("[SYSTEM] Swachh Nayan hardware teardown clean.")


if __name__ == "__main__":
    controller = SwachhNayanController()
    controller.run_main_loop()
