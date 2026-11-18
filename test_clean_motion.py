import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print(">> Clean single-process servo motion test...")
run("echo 0 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null")
run("echo 20000000 > /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null")
run("echo 1000000 > /sys/class/pwm/pwmchip11/pwm0/duty_cycle 2>/dev/null")
run("echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null")

test_angles = [
    (1000000, "0 DEGREES (HOME / RETRACTED)"),
    (1500000, "90 DEGREES (CENTER / DIVERTING)"),
    (2000000, "180 DEGREES (FULL FLAP EXTENSION)"),
    (1500000, "90 DEGREES (CENTER)"),
    (1000000, "0 DEGREES (HOME)")
]

for duty, desc in test_angles:
    print(f"\n>> Sending command: {desc} -> {duty} ns ({duty/1000000.0} ms)")
    run(f"echo {duty} > /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
    cur = run("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
    print(f"   Board register confirmed: {cur} ns")
    time.sleep(3.0)

client.close()
print("\n>> Clean motion test finished successfully!")
