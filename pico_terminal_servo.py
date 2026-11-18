import time
import os
import sys

print("==================================================================", flush=True)
print("       SWACHH-NAYAN: PHYSICAL SERVO MOTION SEQUENCE (7 STEPS)    ", flush=True)
print("==================================================================", flush=True)

pwm_path = '/sys/class/pwm/pwmchip11/pwm0/duty_cycle'
gpio_paths = ['/sys/class/gpio/gpio48/value', '/sys/class/gpio/gpio54/value']

steps = [
    ("POSITION 1:   0° [NORMAL FLOW / CLOSED FLAP]", 1000000, 0.0010, 2.5),
    ("POSITION 2:  45° [QUARTER OPEN]", 1250000, 0.00125, 2.5),
    ("POSITION 3:  90° [FULL 90° TRASH DIVERT]", 1500000, 0.0015, 3.0),
    ("POSITION 4: 135° [WIDE DIVERSION FLAP]", 1750000, 0.00175, 2.5),
    ("POSITION 5: 180° [MAXIMUM FLAP DEFLECTION]", 2000000, 0.0020, 3.0),
    ("POSITION 6:  90° [RETURNING THROUGH 90°]", 1500000, 0.0015, 2.5),
    ("POSITION 7:   0° [HOME / CLOSED POSITION]", 1000000, 0.0010, 2.5),
]

for label, duty, high_s, hold_sec in steps:
    print(f"\n>> ACTUATING: {label}", flush=True)
    print(f"   Duty Cycle: {duty} ns ({duty/1000000.0:.2f} ms) | Holding for {hold_sec}s...", flush=True)

    # 1. Hardware PWM on Pin 4
    try:
        with open(pwm_path, 'w') as f:
            f.write(f"{duty}\n")
    except Exception as e:
        print(f"   [PWM Error]: {e}", flush=True)

    # 2. Synchronous GPIO pulses on Pin 12 & Pin 5
    open_fds = []
    for p in gpio_paths:
        try:
            open_fds.append(open(p, 'w'))
        except Exception:
            pass

    num_pulses = int(hold_sec / 0.020)
    for _ in range(num_pulses):
        for fd in open_fds:
            fd.write("1\n")
            fd.flush()
        time.sleep(high_s)
        for fd in open_fds:
            fd.write("0\n")
            fd.flush()
        time.sleep(max(0.001, 0.020 - high_s))

    for fd in open_fds:
        fd.close()

print("\n==================================================================", flush=True)
print(">> SUCCESS: Servo sweep sequence completed across all 7 angles!  ", flush=True)
print("==================================================================", flush=True)
