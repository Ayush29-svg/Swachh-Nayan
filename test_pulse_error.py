import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

test_script = """
import time
import os

SERVO_GPIO_PIN = 56
pulse_high_s = 0.0015 # 90 deg

p_dir = f"/sys/class/gpio/gpio{SERVO_GPIO_PIN}"
print(f"Checking {p_dir}...")
if not os.path.exists(p_dir):
    print(f"Exporting {SERVO_GPIO_PIN}...")
    with open("/sys/class/gpio/export", "w") as f:
        f.write(f"{SERVO_GPIO_PIN}\\n")
    time.sleep(0.02)

print(f"Setting direction out...")
with open(f"{p_dir}/direction", "w") as f:
    f.write("out\\n")

print(f"Pulsing 40 times at {pulse_high_s*1000}ms...")
with open(f"{p_dir}/value", "w") as f:
    for i in range(40):
        f.write("1\\n")
        f.flush()
        time.sleep(pulse_high_s)
        f.write("0\\n")
        f.flush()
        time.sleep(max(0.001, 0.020 - pulse_high_s))

print("Done pulsing successfully!")
"""

stdin, stdout, stderr = client.exec_command(f"python3 -c \"{test_script}\"")
print("stdout:", stdout.read().decode())
print("stderr:", stderr.read().decode())

client.close()
