import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run_cmd(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

print("=== CHECKING GPIO 54 AND 55 ===")
for p in [54, 55]:
    out, err = run_cmd(f"if [ ! -d /sys/class/gpio/gpio{p} ]; then echo {p} > /sys/class/gpio/export 2>&1; fi; echo out > /sys/class/gpio/gpio{p}/direction; cat /sys/class/gpio/gpio{p}/value")
    print(f"GPIO{p} value: {out} (err: {err})")

print("\n=== CHECKING PWM11 ===")
out, err = run_cmd("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
print(f"PWM duty_cycle: {out}")
out, err = run_cmd("cat /sys/class/pwm/pwmchip11/pwm0/period")
print(f"PWM period: {out}")
out, err = run_cmd("cat /sys/class/pwm/pwmchip11/pwm0/enable")
print(f"PWM enable: {out}")

client.close()
