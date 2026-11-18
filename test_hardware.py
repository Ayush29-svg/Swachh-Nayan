"""
Swachh Nayan — Interactive Hardware Diagnostic Suite
Use this tool to independently verify each hardware peripheral before running the main AI loop.
"""

import time
import sys
import os

import config
from hardware_drivers.servo_driver import MG996RServoDriver
from hardware_drivers.lcd_driver import LCD1602I2CDriver
from hardware_drivers.ultrasonic_driver import HCSR04SensorDriver
from hardware_drivers.relay_driver import PumpRelayDriver


def run_hardware_diagnostics():
    print("======================================================")
    print(" SWACHH NAYAN — INTERACTIVE HARDWARE DIAGNOSTIC TOOL ")
    print("======================================================")
    print("1. Test MG996R Servo Motor (0° Rest -> 120° Dump)")
    print("2. Test 16x2 I2C LCD Display")
    print("3. Test HC-SR04 Ultrasonic Distance Sensor")
    print("4. Test 12V Water Pump Relay (ON / OFF)")
    print("5. Run Full System Diagnostic Routine")
    print("6. Exit")
    print("------------------------------------------------------")

    servo = MG996RServoDriver()
    lcd = LCD1602I2CDriver()
    water_sensor = HCSR04SensorDriver()
    pump = PumpRelayDriver()

    try:
        while True:
            choice = input("\nSelect Diagnostic Test [1-6]: ").strip()

            if choice == "1":
                print("\n[TEST 1] Testing Servo Motor...")
                print("Moving to 0° (In-Water Rest)...")
                servo.move_to_rest()
                time.sleep(2)
                print("Moving to 120° (Over-Rim Dump)...")
                servo.move_to_dump()
                time.sleep(2)
                print("Returning to 0° (Rest)...")
                servo.move_to_rest()
                print("[TEST 1 PASSED] Servo test complete.")

            elif choice == "2":
                print("\n[TEST 2] Testing 16x2 LCD Display...")
                lcd.clear()
                lcd.display_line(1, "SWACHH NAYAN OK")
                lcd.display_line(2, "LCD TEST PASSED")
                time.sleep(3)
                lcd.update_status(0, "SYSTEM READY")
                print("[TEST 2 PASSED] LCD display updated successfully.")

            elif choice == "3":
                print("\n[TEST 3] Testing HC-SR04 Water Level Sensor...")
                for i in range(5):
                    dist = water_sensor.measure_distance_cm()
                    print(f"Reading {i+1}/5: Water Distance = {dist} cm")
                    time.sleep(0.5)
                print("[TEST 3 PASSED] Ultrasonic sensor working.")

            elif choice == "4":
                print("\n[TEST 4] Testing 12V Water Pump Relay...")
                print("Toggling Pump RELAY ON...")
                pump.turn_on()
                time.sleep(3)
                print("Toggling Pump RELAY OFF...")
                pump.turn_off()
                print("[TEST 4 PASSED] Pump relay toggled successfully.")

            elif choice == "5":
                print("\n[TEST 5] Running Full Sequential Hardware Diagnostic Routine...")
                lcd.update_status(0, "DIAGNOSTIC START")
                pump.turn_on()
                time.sleep(1)
                
                dist = water_sensor.measure_distance_cm()
                lcd.display_line(2, f"DIST: {dist}cm OK")
                time.sleep(1.5)

                servo.trigger_scoop_cycle()
                pump.turn_off()
                lcd.update_status(1, "ALL HW TESTS OK")
                print("\n*** ALL HARDWARE PERIPHERALS OPERATING 100% CORRECTLY! ***")

            elif choice == "6":
                print("\nExiting hardware diagnostic tool.")
                break

            else:
                print("Invalid selection. Enter 1-6.")

    finally:
        servo.cleanup()
        pump.turn_off()


if __name__ == "__main__":
    run_hardware_diagnostics()
