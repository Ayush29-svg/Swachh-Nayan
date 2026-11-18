import paramiko
import time
import urllib.request

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def check_vals():
    stdin, stdout, stderr = client.exec_command("cat /sys/class/gpio/gpio54/value; cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
    lines = stdout.read().decode().strip().split("\n")
    print(f"GPIO54 (Relay): {lines[0]} | PWM duty_cycle (Servo): {lines[1] if len(lines)>1 else 'N/A'}")

print("Initial values:")
check_vals()

print("\nCalling port 8088 /api/set_motor (OFF)...")
req = urllib.request.Request("http://172.32.0.93:8088/api/set_motor", data=b'{"state":"OFF"}', headers={"Content-Type":"application/json"})
urllib.request.urlopen(req)
time.sleep(1)
check_vals()

print("\nCalling port 8088 /api/set_motor (ON)...")
req = urllib.request.Request("http://172.32.0.93:8088/api/set_motor", data=b'{"state":"ON"}', headers={"Content-Type":"application/json"})
urllib.request.urlopen(req)
time.sleep(1)
check_vals()

client.close()
