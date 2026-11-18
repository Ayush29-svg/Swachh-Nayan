import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("1. Preparing Hardware PWM11 on Pin 4...")
run("echo 55 > /sys/class/gpio/unexport 2>/dev/null || true")
run("echo 0 > /sys/class/pwm/pwmchip11/export 2>/dev/null || true")
run("echo 20000000 > /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null || true")
run("echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null || true")

print("2. Preparing GPIO56 on Pin 35...")
run("echo 56 > /sys/class/gpio/export 2>/dev/null || true")
run("echo out > /sys/class/gpio/gpio56/direction 2>/dev/null || true")

# Send continuous sweeping pulses to both Pin 4 and Pin 35
sweep_script = """
import time
import os

print('Starting 10-second continuous servo sweep on BOTH Pin 4 (Hardware PWM11) and Pin 35 (GPIO56)...')
val_path_35 = '/sys/class/gpio/gpio56/value'
pwm_path_4 = '/sys/class/pwm/pwmchip11/pwm0/duty_cycle'

steps = [
    (1000000, 0.0010), # 0 deg
    (1500000, 0.0015), # 90 deg
    (2000000, 0.0020), # 180 deg
    (1500000, 0.0015), # 90 deg
    (1000000, 0.0010), # 0 deg
]

for cycle in range(3):
    for duty_ns, high_s in steps:
        # Write Hardware PWM11
        try:
            with open(pwm_path_4, 'w') as f:
                f.write(f'{duty_ns}\\n')
        except Exception:
            pass

        # Write 25 pulses to Pin 35
        try:
            with open(val_path_35, 'w') as f:
                for _ in range(25):
                    f.write('1\\n')
                    f.flush()
                    time.sleep(high_s)
                    f.write('0\\n')
                    f.flush()
                    time.sleep(max(0.001, 0.020 - high_s))
        except Exception:
            time.sleep(0.5)

print('Servo sweep finished.')
"""

print("Running continuous sweep on Pico...")
stdin, stdout, stderr = client.exec_command(f"python3 -c \"{sweep_script}\"")
print(stdout.read().decode('utf-8', errors='replace'))

client.close()
