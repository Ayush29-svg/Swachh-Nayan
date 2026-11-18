import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

print("Writing 1500000 directly to sysfs...")
stdin, stdout, stderr = client.exec_command("echo 1500000 > /sys/class/pwm/pwmchip11/pwm0/duty_cycle; cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
print("Immediate read:", stdout.read().decode().strip())

for i in range(5):
    time.sleep(0.5)
    stdin, stdout, stderr = client.exec_command("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
    print(f"+{0.5*(i+1)}s: {stdout.read().decode().strip()}")

client.close()
