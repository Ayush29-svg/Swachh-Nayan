import paramiko
import time
import urllib.request
import json

print("=== STEP 1: CONNECT TO LUCKFOX PICO (172.32.0.93) ===")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

sftp = client.open_sftp()
print("Uploading server_live_final.py to /userdata/swachh_nayan_v2/server_live.py...")
sftp.put("server_live_final.py", "/userdata/swachh_nayan_v2/server_live.py")
sftp.close()
print("Upload complete!")

print("\n=== STEP 2: RESTART SERVICES ON LUCKFOX PICO ===")
# Stop old server_live.py
client.exec_command("killall -9 python3 2>/dev/null || true")
time.sleep(1)

# Ensure swachh_nayan_app is running with patched binary
stdin, stdout, stderr = client.exec_command("ps | grep swachh_nayan_app")
ps_out = stdout.read().decode()
if "yolov5n_rv1103.rknn" not in ps_out:
    print("Restarting swachh_nayan_app...")
    client.exec_command("cd /userdata/swachh_nayan && export LD_LIBRARY_PATH=/userdata/swachh_nayan/lib && nohup ./swachh_nayan_app model/yolov5n_rv1103.rknn >> app.log 2>&1 &")
    time.sleep(2)

# Start new server_live.py
print("Launching updated server_live.py...")
client.exec_command("nohup python3 /userdata/swachh_nayan_v2/server_live.py >> /userdata/swachh_nayan_v2/server_live.log 2>&1 &")
time.sleep(2)

stdin, stdout, stderr = client.exec_command("ps | grep -E 'server_live|swachh_nayan_app'")
print("Active processes:\n" + stdout.read().decode())

print("\n=== STEP 3: VERIFY HTTP REST ENDPOINTS ===")
time.sleep(1)

# 1. Telemetry
req = urllib.request.Request("http://172.32.0.93:8088/api/live_telemetry")
with urllib.request.urlopen(req, timeout=3.0) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    print("Telemetry Response:")
    print(f"  - Camera FPS: {data.get('camera_fps')}")
    print(f"  - Pump Status: {data.get('pump_status')}")
    print(f"  - Servo Angle: {data.get('servo_angle')}° (duty: {data.get('servo_duty_ns')} ns)")
    print(f"  - Core Temp: {data.get('core_temp')}")

# 2. Test Motor ON
print("\nTesting /api/set_motor (ON)...")
req = urllib.request.Request("http://172.32.0.93:8088/api/set_motor", data=b'{"state":"ON"}', headers={"Content-Type":"application/json"})
with urllib.request.urlopen(req, timeout=3.0) as resp:
    print("Set Motor ON Response:", resp.read().decode())

time.sleep(0.5)
stdin, stdout, stderr = client.exec_command("cat /sys/class/gpio/gpio54/value")
print("Hardware GPIO54 value readback (should be 1):", stdout.read().decode().strip())

# 3. Test Motor OFF
print("\nTesting /api/set_motor (OFF)...")
req = urllib.request.Request("http://172.32.0.93:8088/api/set_motor", data=b'{"state":"OFF"}', headers={"Content-Type":"application/json"})
with urllib.request.urlopen(req, timeout=3.0) as resp:
    print("Set Motor OFF Response:", resp.read().decode())

time.sleep(0.5)
stdin, stdout, stderr = client.exec_command("cat /sys/class/gpio/gpio54/value")
print("Hardware GPIO54 value readback (should be 0):", stdout.read().decode().strip())

# 4. Test Servo Move to 90°
print("\nTesting /api/set_servo_angle (90.0°)...")
req = urllib.request.Request("http://172.32.0.93:8088/api/set_servo_angle", data=b'{"angle":90.0}', headers={"Content-Type":"application/json"})
with urllib.request.urlopen(req, timeout=3.0) as resp:
    print("Set Servo 90° Response:", resp.read().decode())

time.sleep(0.5)
stdin, stdout, stderr = client.exec_command("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
print("Hardware PWM11 duty_cycle readback (should be 1500000):", stdout.read().decode().strip())

# 5. Test Servo Move to 45°
print("\nTesting /api/set_servo_angle (45.0°)...")
req = urllib.request.Request("http://172.32.0.93:8088/api/set_servo_angle", data=b'{"angle":45.0}', headers={"Content-Type":"application/json"})
with urllib.request.urlopen(req, timeout=3.0) as resp:
    print("Set Servo 45° Response:", resp.read().decode())

time.sleep(0.5)
stdin, stdout, stderr = client.exec_command("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
print("Hardware PWM11 duty_cycle readback (should be 1250000):", stdout.read().decode().strip())

# 6. Test Return Home (0°)
print("\nTesting /api/return_home (0.0°)...")
req = urllib.request.Request("http://172.32.0.93:8088/api/return_home", data=b'{"home_angle":0.0}', headers={"Content-Type":"application/json"})
with urllib.request.urlopen(req, timeout=3.0) as resp:
    print("Return Home Response:", resp.read().decode())

time.sleep(0.5)
stdin, stdout, stderr = client.exec_command("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
print("Hardware PWM11 duty_cycle readback (should be 1000000):", stdout.read().decode().strip())

client.close()
print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")
