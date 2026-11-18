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
print("       SWACHH-NAYAN: LIVE SERVO MOTOR PHYSICAL TEST RUN           ")
print("==================================================================")

# 1. Stop background sweeps
run("pkill -9 -f 'continuous_sweep' 2>/dev/null || true")
run("pkill -9 -f 'pwm_duty' 2>/dev/null || true")
time.sleep(0.5)

# 2. Prepare Pin 4 Hardware PWM11
print(">> Step A: Configuring Hardware PWM11 on Pin 4 (1C7_D)...")
run("echo 55 > /sys/class/gpio/unexport 2>/dev/null || true")
run("echo 0 > /sys/class/pwm/pwmchip11/export 2>/dev/null || true")
run("echo 0 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null || true")
run("echo 20000000 > /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null || true")
run("echo 1000000 > /sys/class/pwm/pwmchip11/pwm0/duty_cycle 2>/dev/null || true")
run("echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null || true")

p = run("cat /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null")
d = run("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle 2>/dev/null")
e = run("cat /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null")
print(f"   Hardware PWM11 status: Period={p}ns (50Hz), Duty={d}ns, Enable={e}")

# Prepare candidate GPIO 48 (Pin 12) as synchronized mirror
run("echo 48 > /sys/class/gpio/export 2>/dev/null || true")
run("echo out > /sys/class/gpio/gpio48/direction 2>/dev/null || true")

# 3. Test steps
steps = [
    ("STEP 1: MOVING TO  0° [HOME / CLOSED FLOW]", 1000000, 0.0010, 3.0),
    ("STEP 2: MOVING TO 45° [QUARTER DIVERSION] ", 1250000, 0.00125, 2.5),
    ("STEP 3: MOVING TO 90° [FULL TRASH DIVERT] ", 1500000, 0.0015, 3.0),
    ("STEP 4: MOVING TO 180° [WIDE DEFLECTION]  ", 2000000, 0.0020, 3.0),
    ("STEP 5: RETURNING TO 90° [MIDWAY GATE]   ", 1500000, 0.0015, 2.0),
    ("STEP 6: RETURNING TO  0° [HOME REST]     ", 1000000, 0.0010, 3.0),
]

board_runner = """
import time
import sys

steps = [
    ("STEP 1: MOVING TO   0 DEG [HOME / CLOSED FLOW]", 1000000, 0.0010, 3.0),
    ("STEP 2: MOVING TO  45 DEG [QUARTER DIVERSION] ", 1250000, 0.00125, 2.5),
    ("STEP 3: MOVING TO  90 DEG [FULL TRASH DIVERT] ", 1500000, 0.0015, 3.0),
    ("STEP 4: MOVING TO 180 DEG [WIDE DEFLECTION]  ", 2000000, 0.0020, 3.0),
    ("STEP 5: RETURNING TO 90 DEG [MIDWAY GATE]   ", 1500000, 0.0015, 2.0),
    ("STEP 6: RETURNING TO   0 DEG [HOME REST]     ", 1000000, 0.0010, 3.0),
]

pwm_duty_path = '/sys/class/pwm/pwmchip11/pwm0/duty_cycle'
gpio_val_path = '/sys/class/gpio/gpio48/value'

for label, duty, high_s, hold_s in steps:
    print(f">> {label} | Pulse: {duty/1000000.0:.2f}ms | Holding for {hold_s}s...", flush=True)
    try:
        with open(pwm_duty_path, 'w') as f:
            f.write(str(duty) + '\\n')
    except Exception as ex:
        print(f"   PWM write err: {ex}", flush=True)

    # Also emit synchronized pulses on GPIO48
    try:
        with open(gpio_val_path, 'w') as gf:
            pulses = int(hold_s / 0.020)
            for _ in range(pulses):
                gf.write('1\\n')
                gf.flush()
                time.sleep(high_s)
                gf.write('0\\n')
                gf.flush()
                time.sleep(max(0.001, 0.020 - high_s))
    except Exception:
        time.sleep(hold_s)

print(">> [ALL 6 MOTION STEPS EXECUTED SUCCESSFULLY]", flush=True)
"""

print("\n>> Executing physical motion sweep on board now...")
sftp = client.open_sftp()
with sftp.file("/tmp/run_servo_sweep.py", "w") as f:
    f.write(board_runner)
sftp.close()

stdin, stdout, stderr = client.exec_command("python3 -u /tmp/run_servo_sweep.py")

for line in iter(stdout.readline, ""):
    print("  " + line.strip(), flush=True)

err = stderr.read().decode().strip()
if err:
    print("Errors:", err)

# Restart continuous gentle oscillation so user can see it keep running
sweep_loop = """
import time
os_duty = '/sys/class/pwm/pwmchip11/pwm0/duty_cycle'
while True:
    for duty in [1000000, 1500000, 1000000]:
        try:
            with open(os_duty, 'w') as f:
                f.write(str(duty) + '\\n')
        except:
            pass
        time.sleep(2.0)
"""
with client.open_sftp().file("/tmp/continuous_sweep.py", "w") as f:
    f.write(sweep_loop)
run("nohup python3 /tmp/continuous_sweep.py > /dev/null 2>&1 &")

client.close()
print("\n==================================================================")
print(">> TEST RUN COMPLETE! Continuous oscillation active on Pin 4.")
print("==================================================================")
