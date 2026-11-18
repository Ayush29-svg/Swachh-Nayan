import paramiko
import time
import sys

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("1. Uploading test script to Luckfox Pico...")
sftp = client.open_sftp()
sftp.put("pico_terminal_servo.py", "/tmp/pico_terminal_servo.py")
sftp.close()

print("2. Preparing Hardware PWM11 and GPIOs...")
run("pkill -f 'pwm_duty' 2>/dev/null || true")
run("echo 55 > /sys/class/gpio/unexport 2>/dev/null || true")
run("echo 0 > /sys/class/pwm/pwmchip11/export 2>/dev/null || true")
run("echo 20000000 > /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null || true")
run("echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null || true")
for g in [48, 54]:
    run(f"echo {g} > /sys/class/gpio/export 2>/dev/null || true")
    run(f"echo out > /sys/class/gpio/gpio{g}/direction 2>/dev/null || true")

print("3. Executing live physical servo test now...\n")
stdin, stdout, stderr = client.exec_command("python3 -u /tmp/pico_terminal_servo.py")

for line in iter(stdout.readline, ""):
    print(line, end="", flush=True)

err = stderr.read().decode('utf-8', errors='replace').strip()
if err:
    print("\nSTDERR:", err)

# Ensure server_live.py is running
ps_srv = run("ps | grep server_live.py | grep -v grep")
if not ps_srv:
    run("nohup python3 -u /userdata/swachh_nayan_v2/server_live.py >> /userdata/swachh_nayan_v2/server_live.log 2>&1 &")

client.close()
