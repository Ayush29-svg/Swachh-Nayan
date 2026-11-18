import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("Setting up live continuous PWM oscillation on Pin 4...")
# Set up a background loop on the Pico that moves PWM11 between 0 deg (1.0ms) and 90 deg (1.5ms) every 2 seconds
sweep_script = """
import time
import os

os.system("echo 55 > /sys/class/gpio/unexport 2>/dev/null")
os.system("echo 0 > /sys/class/pwm/pwmchip11/export 2>/dev/null")
os.system("echo 20000000 > /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null")
os.system("echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null")

angles = [(1000000, "0 DEG (REST)"), (1500000, "90 DEG (DIVERT)"), (2000000, "180 DEG (WIDE OPEN)")]

while True:
    for duty, name in angles:
        try:
            with open("/sys/class/pwm/pwmchip11/pwm0/duty_cycle", "w") as f:
                f.write(str(duty) + "\\n")
        except Exception:
            pass
        time.sleep(1.5)
"""

run("pkill -f 'continuous_sweep.py' 2>/dev/null || true")
run(f"cat << 'EOF' > /tmp/continuous_sweep.py\n{sweep_script}\nEOF")
run("nohup python3 /tmp/continuous_sweep.py > /dev/null 2>&1 &")

ps = run("ps | grep continuous_sweep")
print("Continuous sweep process:\n" + ps)

client.close()
print("Live continuous sweep is NOW RUNNING on Pin 4!")
