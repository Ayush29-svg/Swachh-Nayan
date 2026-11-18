import paramiko
import time
import urllib.request
import json

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def get_duty():
    stdin, stdout, stderr = client.exec_command("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
    return stdout.read().decode().strip()

print("Initial duty:", get_duty())

print("Sending angle 90° (duty should be 1500000)...")
req = urllib.request.Request("http://172.32.0.93:8088/api/set_servo_angle", data=b'{"angle": 90.0}', headers={"Content-Type":"application/json"})
urllib.request.urlopen(req)

for i in range(10):
    time.sleep(0.3)
    print(f"Time +{0.3*(i+1):.1f}s duty: {get_duty()}")

client.close()
