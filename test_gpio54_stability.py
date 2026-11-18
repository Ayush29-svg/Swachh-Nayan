import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run_cmd(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("Setting GPIO54 to 1 (Relay ON)...")
run_cmd("echo 1 > /sys/class/gpio/gpio54/value")
time.sleep(0.5)
print("Initial:", run_cmd("cat /sys/class/gpio/gpio54/value"))

for i in range(5):
    time.sleep(0.5)
    print(f"+{(i+1)*0.5}s:", run_cmd("cat /sys/class/gpio/gpio54/value"))

print("\nSetting GPIO54 to 0 (Relay OFF)...")
run_cmd("echo 0 > /sys/class/gpio/gpio54/value")
time.sleep(0.5)
print("Initial:", run_cmd("cat /sys/class/gpio/gpio54/value"))

for i in range(5):
    time.sleep(0.5)
    print(f"+{(i+1)*0.5}s:", run_cmd("cat /sys/class/gpio/gpio54/value"))

client.close()
