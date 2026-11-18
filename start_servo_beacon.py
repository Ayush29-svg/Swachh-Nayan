import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("Launching 3-minute continuous servo sweep beacon on Pin 4 (Hardware PWM11)...")

# Ensure PWM11 is enabled at 50Hz on Pin 4
run("echo 55 > /sys/class/gpio/unexport 2>/dev/null || true")
run("echo 0 > /sys/class/pwm/pwmchip11/export 2>/dev/null || true")
run("echo 20000000 > /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null || true")
run("echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null || true")

beacon_script = """
import time

pwm_duty = '/sys/class/pwm/pwmchip11/pwm0/duty_cycle'

# Continuous sweep between 30 deg and 150 deg every 1 second for 180 seconds
start_t = time.time()
while time.time() - start_t < 180:
    for duty, deg in [(1166667, 30), (1500000, 90), (1833333, 150), (1500000, 90)]:
        with open(pwm_duty, 'w') as f:
            f.write(f'{duty}\\n')
        time.sleep(1.0)
"""

# Launch in background on Pico
stdin, stdout, stderr = client.exec_command(f"nohup python3 -c \"{beacon_script}\" >/dev/null 2>&1 &")
client.close()

print("Continuous servo beacon is now LIVE and pulsing Pin 4 continuously for the next 3 minutes!")
