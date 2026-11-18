import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("Preparing Omni-Pin Pulse Test...")
# Unexport 55 for PWM11
run("echo 55 > /sys/class/gpio/unexport 2>/dev/null || true")
run("echo 0 > /sys/class/pwm/pwmchip11/export 2>/dev/null || true")
run("echo 20000000 > /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null || true")
run("echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null || true")

# Export candidate GPIOs: 48 (Pin 12), 49 (Pin 14), 54 (Pin 5), 56 (Pin 19), 57 (Pin 20)
for g in [48, 49, 54, 56, 57]:
    run(f"echo {g} > /sys/class/gpio/export 2>/dev/null || true")
    run(f"echo out > /sys/class/gpio/gpio{g}/direction 2>/dev/null || true")

omni_script = """
import time
import os

pwm_path = '/sys/class/pwm/pwmchip11/pwm0/duty_cycle'
gpio_pins = [48, 49, 54, 56, 57]
gpio_paths = [f'/sys/class/gpio/gpio{g}/value' for g in gpio_pins]

print('>>> STARTING OMNI-PIN SERVO SWEEP <<<', flush=True)
print('Pulsing Pin 4 (Hardware PWM11) AND GPIOs [48, 49, 54, 56, 57] simultaneously...', flush=True)

angles = [
    (0, 1000000, 0.0010),
    (90, 1500000, 0.0015),
    (180, 2000000, 0.0020),
    (90, 1500000, 0.0015),
    (0, 1000000, 0.0010),
]

for cycle in range(3):
    print(f'-- Cycle {cycle+1}/3 --', flush=True)
    for ang, duty_ns, high_s in angles:
        print(f'   Moving to {ang}°...', flush=True)
        # 1. Hardware PWM11
        try:
            with open(pwm_path, 'w') as f:
                f.write(f'{duty_ns}\\n')
        except Exception:
            pass

        # 2. Pulse all candidate GPIOs
        open_fds = []
        for p in gpio_paths:
            try:
                open_fds.append(open(p, 'w'))
            except Exception:
                pass

        for _ in range(35):
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

print('>>> OMNI-PIN SERVO SWEEP FINISHED <<<', flush=True)
"""

stdin, stdout, stderr = client.exec_command(f"python3 -c \"{omni_script}\"")
print(stdout.read().decode('utf-8', errors='replace'))

client.close()
