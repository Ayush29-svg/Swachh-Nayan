import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def exec_cmd(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    return out

print("--- Testing GPIO54 directly ---")
exec_cmd("if [ ! -d /sys/class/gpio/gpio54 ]; then echo 54 > /sys/class/gpio/export; fi; echo out > /sys/class/gpio/gpio54/direction")
print("Setting GPIO54 = 1 (Relay ON according to test_hardware.sh)...")
exec_cmd("echo 1 > /sys/class/gpio/gpio54/value")
time.sleep(1)
print("GPIO54 readback:", exec_cmd("cat /sys/class/gpio/gpio54/value"))

time.sleep(1)
print("Setting GPIO54 = 0 (Relay OFF according to test_hardware.sh)...")
exec_cmd("echo 0 > /sys/class/gpio/gpio54/value")
time.sleep(1)
print("GPIO54 readback:", exec_cmd("cat /sys/class/gpio/gpio54/value"))

print("\n--- Testing PWM11 directly ---")
# 1. Ensure gpio55 is NOT exported
exec_cmd("if [ -d /sys/class/gpio/gpio55 ]; then echo 55 > /sys/class/gpio/unexport; fi")
# 2. Check PWM
exec_cmd("if [ ! -d /sys/class/pwm/pwmchip11/pwm0 ]; then echo 0 > /sys/class/pwm/pwmchip11/export; fi")
exec_cmd("echo 20000000 > /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null || true")
exec_cmd("echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null || true")

for duty, angle in [(1000000, "0°"), (1500000, "90°"), (2000000, "180°"), (1000000, "0°")]:
    print(f"Setting PWM11 duty {duty} ({angle})...")
    exec_cmd(f"echo {duty} > /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
    time.sleep(1)
    print("PWM duty readback:", exec_cmd("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle"))

client.close()
