import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("Exporting all candidate GPIOs: 54, 55, 56, 57, 58, 59...")
for p in [54, 55, 56, 57, 58, 59]:
    run(f"echo {p} > /sys/class/gpio/export 2>/dev/null || true")
    run(f"echo out > /sys/class/gpio/gpio{p}/direction 2>/dev/null || true")

print("Candidate GPIO exported states:")
for p in [54, 55, 56, 57, 58, 59]:
    val = run(f"cat /sys/class/gpio/gpio{p}/value 2>/dev/null")
    print(f"  GPIO {p}: value={val}")

client.close()
