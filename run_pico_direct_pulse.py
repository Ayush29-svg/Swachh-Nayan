import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

sftp = client.open_sftp()
with sftp.open('/userdata/swachh_nayan_v2/test_direct_pulse.py', 'w') as f:
    f.write('''import time
import os

SERVO_GPIO_PIN = 56
pulse_high_s = 0.0015

p_dir = f"/sys/class/gpio/gpio{SERVO_GPIO_PIN}"
print(f"Checking {p_dir}...")
if not os.path.exists(p_dir):
    print(f"Exporting {SERVO_GPIO_PIN}...")
    with open("/sys/class/gpio/export", "w") as ef:
        ef.write(f"{SERVO_GPIO_PIN}\\n")
    time.sleep(0.05)

with open(f"{p_dir}/direction", "w") as df:
    df.write("out\\n")

print(f"Pulsing 40 times on GPIO56...")
with open(f"{p_dir}/value", "w") as vf:
    for i in range(40):
        vf.write("1\\n")
        vf.flush()
        time.sleep(pulse_high_s)
        vf.write("0\\n")
        vf.flush()
        time.sleep(max(0.001, 0.020 - pulse_high_s))

print("Pulse test complete!")
''')
sftp.close()

stdin, stdout, stderr = client.exec_command("python3 /userdata/swachh_nayan_v2/test_direct_pulse.py")
print("stdout:", stdout.read().decode())
print("stderr:", stderr.read().decode())

client.close()
