import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

# Prepare Pin 4 (Hardware PWM11)
run("echo 55 > /sys/class/gpio/unexport 2>/dev/null || true")
run("echo 0 > /sys/class/pwm/pwmchip11/export 2>/dev/null || true")
run("echo 20000000 > /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null || true")
run("echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null || true")

# Prepare candidate GPIOs: 48 (Pin 12), 54 (Pin 5)
for g in [48, 54]:
    run(f"echo {g} > /sys/class/gpio/export 2>/dev/null || true")
    run(f"echo out > /sys/class/gpio/gpio{g}/direction 2>/dev/null || true")

beacon_script = """
import time
import os

pwm_duty = '/sys/class/pwm/pwmchip11/pwm0/duty_cycle'
gpio_paths = ['/sys/class/gpio/gpio48/value', '/sys/class/gpio/gpio54/value']

# Run continuous 5-minute omni-sweep
start_t = time.time()
while time.time() - start_t < 300:
    for duty, high_s, deg in [(1000000, 0.0010, 0), (1500000, 0.0015, 90), (2000000, 0.0020, 180), (1500000, 0.0015, 90)]:
        # 1. Hardware PWM on Pin 4
        try:
            with open(pwm_duty, 'w') as f:
                f.write(f'{duty}\\n')
        except Exception:
            pass

        # 2. GPIO bit-bang on Pin 12 & Pin 5
        open_fds = []
        for p in gpio_paths:
            try:
                open_fds.append(open(p, 'w'))
            except Exception:
                pass

        for _ in range(25):
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

        time.sleep(0.3)
"""

stdin, stdout, stderr = client.exec_command(f"nohup python3 -c \"{beacon_script}\" >/dev/null 2>&1 &")
client.close()
print("Continuous omni-sweep beacon started for 5 minutes!")
