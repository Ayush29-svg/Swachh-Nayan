import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

print("1. Checking if swachh_nayan_app is running:")
stdin, stdout, stderr = client.exec_command("ps | grep swachh_nayan_app")
print(stdout.read().decode())

print("2. Stopping swachh_nayan_app...")
client.exec_command("killall -9 swachh_nayan_app 2>/dev/null")
time.sleep(1)

print("3. Testing direct write to PWM duty_cycle (1500000 = 90°)...")
client.exec_command("echo 1500000 > /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
time.sleep(0.5)

stdin, stdout, stderr = client.exec_command("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
print("Duty cycle read back:", stdout.read().decode().strip())

for i in range(5):
    time.sleep(0.5)
    stdin, stdout, stderr = client.exec_command("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
    print(f"+{0.5*(i+1)}s duty: {stdout.read().decode().strip()}")

client.close()
