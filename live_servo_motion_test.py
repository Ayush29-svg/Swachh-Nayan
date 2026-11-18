import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("==============================================================")
print(" SWACHH-NAYAN: LIVE SERVO ACTUATION TEST ON PIN 4 (PWM11)")
print(" Watch your servo motor horn rotate across the angles below!   ")
print("==============================================================")

# Ensure Pin 4 is in Hardware PWM mode
run("echo 55 > /sys/class/gpio/unexport 2>/dev/null || true")
run("echo 0 > /sys/class/pwm/pwmchip11/export 2>/dev/null || true")
run("echo 20000000 > /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null || true")
run("echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null || true")

test_script = """
import time
import os

pwm_duty = '/sys/class/pwm/pwmchip11/pwm0/duty_cycle'

steps = [
    ('0° (REST / CLOSED FLAP)', 1000000, 2.0),
    ('45° (QUARTER OPEN)', 1250000, 2.0),
    ('90° (HALF / FULL DIVERT)', 1500000, 2.0),
    ('135° (WIDE DIVERSION)', 1750000, 2.0),
    ('180° (MAXIMUM DEFLECTION)', 2000000, 2.0),
    ('90° (RETURNING BACK)', 1500000, 1.5),
    ('0° (REST POSITION)', 1000000, 1.5),
]

for label, duty, pause in steps:
    print(f'>> ACTUATING SERVO: {label} | Duty: {duty} ns ({duty/1000000.0:.2f} ms)...', flush=True)
    with open(pwm_duty, 'w') as f:
        f.write(f'{duty}\\n')
    time.sleep(pause)

print('>> Live servo motion sequence complete!')
"""

stdin, stdout, stderr = client.exec_command(f"python3 -c \"{test_script}\"")
print(stdout.read().decode('utf-8', errors='replace'))

client.close()
