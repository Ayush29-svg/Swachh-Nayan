import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("Testing Relay Click (GPIO 54)...")
run("echo 54 > /sys/class/gpio/export 2>/dev/null || true")
run("echo out > /sys/class/gpio/gpio54/direction 2>/dev/null || true")

for i in range(3):
    print(f"Cycle {i+1}: Clicking Relay ON (val=1)...")
    run("echo 1 > /sys/class/gpio/gpio54/value")
    time.sleep(1.0)
    print(f"Cycle {i+1}: Clicking Relay OFF (val=0)...")
    run("echo 0 > /sys/class/gpio/gpio54/value")
    time.sleep(1.0)

client.close()
print("Relay test complete.")
