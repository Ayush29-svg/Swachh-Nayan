import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

print("Writing 0 to GPIO54 (Relay ON)...")
stdin, stdout, stderr = client.exec_command("echo 0 > /sys/class/gpio/gpio54/value; cat /sys/class/gpio/gpio54/value")
print("Immediate read:", stdout.read().decode().strip())

for i in range(5):
    time.sleep(0.5)
    stdin, stdout, stderr = client.exec_command("cat /sys/class/gpio/gpio54/value")
    print(f"+{0.5*(i+1)}s: {stdout.read().decode().strip()}")

print("\nWriting 1 to GPIO54 (Relay OFF)...")
stdin, stdout, stderr = client.exec_command("echo 1 > /sys/class/gpio/gpio54/value; cat /sys/class/gpio/gpio54/value")
print("Immediate read:", stdout.read().decode().strip())

for i in range(5):
    time.sleep(0.5)
    stdin, stdout, stderr = client.exec_command("cat /sys/class/gpio/gpio54/value")
    print(f"+{0.5*(i+1)}s: {stdout.read().decode().strip()}")

client.close()
