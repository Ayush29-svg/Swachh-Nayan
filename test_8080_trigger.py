import urllib.request
import time
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def get_duty():
    stdin, stdout, stderr = client.exec_command("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
    return stdout.read().decode().strip()

print("Initial duty:", get_duty())

try:
    print("Calling http://172.32.0.93:8080/api/trigger_gate ...")
    req = urllib.request.Request("http://172.32.0.93:8080/api/trigger_gate", data=b'', method="POST")
    res = urllib.request.urlopen(req, timeout=2)
    print("Response:", res.read().decode())
except Exception as e:
    print("Error:", e)

for i in range(10):
    time.sleep(0.3)
    print(f"+{0.3*(i+1):.1f}s duty: {get_duty()}")

client.close()
