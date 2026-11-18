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
print("     SWACHH-NAYAN: CONTINUOUS SERVO SWEEP ON PIN 4 & PIN 5        ")
print("==================================================================")

# 1. Hardware PWM on Pin 4
run("echo 0 > /sys/class/pwm/pwmchip11/export 2>/dev/null || true")
run("echo 20000000 > /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null || true")
run("echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null || true")

# 2. GPIO on Pin 5
run("echo 54 > /sys/class/gpio/export 2>/dev/null || true")
run("echo out > /sys/class/gpio/gpio54/direction 2>/dev/null || true")

runner_code = """
import time
import sys

pwm_path = '/sys/class/pwm/pwmchip11/pwm0/duty_cycle'
gpio_path = '/sys/class/gpio/gpio54/value'

positions = [
    (1000000, 0.0010, '>>> [0 DEGREE - HOME REST]    '),
    (1250000, 0.00125, '>>> [45 DEGREE - QUARTER FLAP]'),
    (1500000, 0.0015, '>>> [90 DEGREE - TRASH DIVERT]'),
    (1750000, 0.00175, '>>> [135 DEGREE - WIDE GATE]  '),
    (2000000, 0.0020, '>>> [180 DEGREE - MAX OPEN]   '),
    (1500000, 0.0015, '>>> [90 DEGREE - RETURNING]   '),
    (1000000, 0.0010, '>>> [0 DEGREE - BACK HOME]    '),
]

pwm_f = open(pwm_path, 'w')
gpio_f = open(gpio_path, 'w')

print('Active continuous sweep started across Pin 4 & Pin 5...', flush=True)

# Run 4 full cycles (about 60 seconds total)
for cycle in range(1, 5):
    print(f'\\n=== STARTING SWEEP CYCLE {cycle} OF 4 ===', flush=True)
    for duty, high_s, label in positions:
        print(f'{label} | Pulse: {duty/1000000.0:.2f}ms | Holding 2s...', flush=True)
        # Update Hardware PWM11 (Pin 4)
        pwm_f.seek(0)
        pwm_f.write(str(duty) + '\\n')
        pwm_f.flush()

        # Update GPIO54 (Pin 5) at 50Hz for 2 seconds
        t_end = time.time() + 2.0
        while time.time() < t_end:
            gpio_f.seek(0)
            gpio_f.write('1\\n')
            gpio_f.flush()
            time.sleep(high_s)
            gpio_f.seek(0)
            gpio_f.write('0\\n')
            gpio_f.flush()
            time.sleep(max(0.001, 0.020 - high_s))

pwm_f.close()
gpio_f.close()
print('\\n=== SWEEP COMPLETED SUCCESSFULLY ===', flush=True)
"""

with client.open_sftp().file('/tmp/active_sweep.py', 'w') as f:
    f.write(runner_code)

print("Starting live synchronized sweep stream now...")
stdin, stdout, stderr = client.exec_command("python3 -u /tmp/active_sweep.py")

for line in iter(stdout.readline, ""):
    print("  " + line.strip(), flush=True)

err = stderr.read().decode().strip()
if err:
    print("Errors:", err)

client.close()
