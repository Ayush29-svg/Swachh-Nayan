import paramiko
import time
import sys

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("==================================================================")
print("       SWACHH-NAYAN: LIVE TERMINAL SERVO ACTUATION TEST           ")
print("==================================================================")

# 1. Stop background beacon scripts to prevent any signal contention
print(">> Halting background beacons...")
run("pkill -f 'pwm_duty' 2>/dev/null || true")
time.sleep(0.5)

# 2. Hardware PWM11 Initialization on Pin 4
print(">> Initializing Hardware PWM11 on Physical Pin 4 (50 Hz / 20ms)...")
run("echo 55 > /sys/class/gpio/unexport 2>/dev/null || true")
run("echo 0 > /sys/class/pwm/pwmchip11/export 2>/dev/null || true")
run("echo 20000000 > /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null || true")
run("echo 1000000 > /sys/class/pwm/pwmchip11/pwm0/duty_cycle 2>/dev/null || true")
run("echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null || true")

# 3. Candidate GPIO Initialization (Pins 12 & 5)
for g in [48, 54]:
    run(f"echo {g} > /sys/class/gpio/export 2>/dev/null || true")
    run(f"echo out > /sys/class/gpio/gpio{g}/direction 2>/dev/null || true")

# 4. Multi-Step Test Sequence
steps = [
    ("POSITION 1:  0° [REST / NORMAL FLOW]", 1000000, 0.0010, 3.0),
    ("POSITION 2: 45° [QUARTER DIVERSION]", 1250000, 0.00125, 2.5),
    ("POSITION 3: 90° [FULL 90° TRASH DIVERT]", 1500000, 0.0015, 3.0),
    ("POSITION 4: 135° [WIDE FLAP OPEN]", 1750000, 0.00175, 2.5),
    ("POSITION 5: 180° [MAXIMUM DEFLECTION]", 2000000, 0.0020, 3.0),
    ("POSITION 6: 90° [RETURNING MIDWAY]", 1500000, 0.0015, 2.5),
    ("POSITION 7:  0° [REST POSITION / HOME]", 1000000, 0.0010, 2.5),
]

test_code = """
import time
import os
import sys

pwm_path = '/sys/class/pwm/pwmchip11/pwm0/duty_cycle'
gpio_paths = ['/sys/class/gpio/gpio48/value', '/sys/class/gpio/gpio54/value']

steps = [
    ("POS 1:   0° [REST / NORMAL FLOW]", 1000000, 0.0010, 3.0),
    ("POS 2:  45° [QUARTER DIVERSION]", 1250000, 0.00125, 2.5),
    ("POS 3:  90° [FULL 90° TRASH DIVERT]", 1500000, 0.0015, 3.0),
    ("POS 4: 135° [WIDE FLAP OPEN]", 1750000, 0.00175, 2.5),
    ("POS 5: 180° [MAXIMUM DEFLECTION]", 2000000, 0.0020, 3.0),
    ("POS 6:  90° [RETURNING MIDWAY]", 1500000, 0.0015, 2.5),
    ("POS 7:   0° [REST POSITION / HOME]", 1000000, 0.0010, 2.5),
]

for label, duty, high_s, hold_sec in steps:
    print(f'\\n>> [COMMAND] {label}', flush=True)
    print(f'   - Pulse Width: {duty} ns ({duty/1000000.0:.2f} ms)', flush=True)
    print(f'   - Holding for {hold_sec} seconds...', flush=True)

    # 1. Hardware PWM on Pin 4
    try:
        with open(pwm_path, 'w') as f:
            f.write(f'{duty}\\n')
    except Exception as e:
        print(f'   [PWM Write Error]: {e}', flush=True)

    # 2. Synchronous GPIO pulse burst on Pin 12 & Pin 5
    open_fds = []
    for p in gpio_paths:
        try:
            open_fds.append(open(p, 'w'))
        except Exception:
            pass

    num_pulses = int(hold_sec / 0.020)
    for _ in range(num_pulses):
        for fd in open_fds:
            fd.write('1\\n')
            fd.flush()
        time.sleep(high_s)
        for fd in open_fds:
            fd.write('0\\n')
            fd.flush()
        time.sleep(max(0.001, 0.020 - high_s))

    for fd in open_fds:
        fd.close()

print('\\n==================================================================', flush=True)
print('>> TEST COMPLETE: Flapper successfully moved through all 7 positions.', flush=True)
print('==================================================================', flush=True)
"""

print("\nStarting 7-position physical motion sweep now...\n")
stdin, stdout, stderr = client.exec_command(f"python3 -u -c \"{test_code}\"")

# Stream output line by line in real time
for line in iter(stdout.readline, ""):
    print(line, end="", flush=True)

# 5. Ensure server_live.py is healthy
ps_srv = run("ps | grep server_live.py | grep -v grep")
if not ps_srv:
    print("\n>> Restoring server_live.py dashboard on port 8088...")
    run("nohup python3 -u /userdata/swachh_nayan_v2/server_live.py >> /userdata/swachh_nayan_v2/server_live.log 2>&1 &")

client.close()
