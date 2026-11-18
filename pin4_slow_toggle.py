import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("Setting Pin 4 & Pin 5 to slow 1Hz On/Off square wave...")
# Pin 4: Hardware PWM with period 1000000000 (1 second), duty 500000000 (0.5 second)
# Or toggle duty between 0 and 20000000 every 1.5 seconds
script = """
import time
import os

p_node = '/sys/class/pwm/pwmchip11/pwm0'
g_val = '/sys/class/gpio/gpio54/value'

# Ensure GPIO54 is exported
os.system('echo 54 > /sys/class/gpio/export 2>/dev/null')
os.system('echo out > /sys/class/gpio/gpio54/direction 2>/dev/null')

# Ensure PWM11 is enabled
os.system('echo 0 > /sys/class/pwm/pwmchip11/export 2>/dev/null')
os.system('echo 20000000 > /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null')
os.system('echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null')

for _ in range(30):
    # HIGH (3.3V) on Pin 4 and Pin 5
    with open(f'{p_node}/duty_cycle', 'w') as f:
        f.write('20000000\\n')
    with open(g_val, 'w') as f:
        f.write('1\\n')
    time.sleep(1.0)

    # LOW (0V) on Pin 4 and Pin 5
    with open(f'{p_node}/duty_cycle', 'w') as f:
        f.write('0\\n')
    with open(g_val, 'w') as f:
        f.write('0\\n')
    time.sleep(1.0)
"""

with client.open_sftp().file('/tmp/slow_toggle.py', 'w') as f:
    f.write(script)

run("nohup python3 /tmp/slow_toggle.py >/dev/null 2>&1 &")
client.close()
print("Slow 1Hz toggle running on Pin 4 & Pin 5 for 60 seconds!")
