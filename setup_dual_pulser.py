import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("Setting up dual Pin 4 (Hardware PWM) + Pin 5 (GPIO 54) synchronous pulsing...")

# 1. Configure Hardware PWM on Pin 4
run("echo 0 > /sys/class/pwm/pwmchip11/export 2>/dev/null || true")
run("echo 20000000 > /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null || true")
run("echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null || true")

# 2. Configure GPIO 54 (Pin 5)
run("echo 54 > /sys/class/gpio/export 2>/dev/null || true")
run("echo out > /sys/class/gpio/gpio54/direction 2>/dev/null || true")

# 3. Dedicated continuous multi-pin pulser
dual_pulser = """
import time
import os

pwm_f = open('/sys/class/pwm/pwmchip11/pwm0/duty_cycle', 'w')
gpio_f = open('/sys/class/gpio/gpio54/value', 'w')

positions = [
    (1000000, 0.0010, '0 DEGREES'),
    (1500000, 0.0015, '90 DEGREES'),
    (2000000, 0.0020, '180 DEGREES'),
    (1500000, 0.0015, '90 DEGREES')
]

# Run 10 full cycles
for cycle in range(10):
    for duty, high_s, name in positions:
        # Hardware PWM update
        pwm_f.seek(0)
        pwm_f.write(str(duty) + '\\n')
        pwm_f.flush()

        # GPIO 54 bit-bang for 2.0 seconds (100 pulses at 50Hz)
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
"""

with client.open_sftp().file('/tmp/dual_pulser.py', 'w') as f:
    f.write(dual_pulser)

print("Dual pulser written to board.")
client.close()
