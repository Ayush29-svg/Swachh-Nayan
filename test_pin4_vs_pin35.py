import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("TEST A: Hardware PWM11 on Physical Pin 4 ALONE...")
run("echo 55 > /sys/class/gpio/unexport 2>/dev/null || true")
run("echo 0 > /sys/class/pwm/pwmchip11/export 2>/dev/null || true")
run("echo 20000000 > /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null || true")
run("echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null || true")

for duty in [1000000, 1500000, 2000000, 1000000]:
    print(f"  Pin 4 PWM duty: {duty} ns...")
    run(f"echo {duty} > /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
    time.sleep(1.5)

print("\nTEST B: Software bit-bang PWM on Physical Pin 35 (GPIO56) ALONE...")
bitbang_script = """
import time
val_path = '/sys/class/gpio/gpio56/value'
for high_s in [0.0010, 0.0015, 0.0020, 0.0010]:
    print(f'  Pin 35 pulsing {high_s*1000:.1f}ms (50 pulses)...')
    with open(val_path, 'w') as f:
        for _ in range(50):
            f.write('1\\n')
            f.flush()
            time.sleep(high_s)
            f.write('0\\n')
            f.flush()
            time.sleep(max(0.001, 0.020 - high_s))
    time.sleep(1.0)
"""
stdin, stdout, stderr = client.exec_command(f"python3 -c \"{bitbang_script}\"")
print(stdout.read().decode('utf-8', errors='replace'))

client.close()
