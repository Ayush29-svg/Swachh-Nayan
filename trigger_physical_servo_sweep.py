import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("Triggering instant physical servo sweep on Luckfox Pico...")

sweep_code = """
import time
import os

pwm_path = '/sys/class/pwm/pwmchip11/pwm0/duty_cycle'
gpio_path = '/sys/class/gpio/gpio56/value'

# Unexport gpio55 so PWM11 has hardware control of Pin 4
os.system('echo 55 > /sys/class/gpio/unexport 2>/dev/null')
os.system('echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null')

positions = [
    (0, 1000000),
    (45, 1250000),
    (90, 1500000),
    (135, 1750000),
    (180, 2000000),
    (90, 1500000),
    (0, 1000000),
]

for cycle in range(2):
    print(f'=== Sweep Cycle {cycle+1}/2 ===')
    for angle, duty in positions:
        print(f'  Moving to {angle}° (duty: {duty} ns)...')
        try:
            with open(pwm_path, 'w') as f:
                f.write(f'{duty}\\n')
        except Exception as e:
            print('  PWM write error:', e)
        
        # Also bit-bang Pin 35/GPIO56
        try:
            high_s = duty / 1e9
            with open(gpio_path, 'w') as f:
                for _ in range(30):
                    f.write('1\\n')
                    f.flush()
                    time.sleep(high_s)
                    f.write('0\\n')
                    f.flush()
                    time.sleep(max(0.001, 0.020 - high_s))
        except Exception:
            time.sleep(0.6)
        
        time.sleep(0.4)

print('Physical sweep complete.')
"""

stdin, stdout, stderr = client.exec_command(f"python3 -c \"{sweep_code}\"")
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
