import paramiko
import requests
import time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = c.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("==============================================================")
print(" SWACHH-NAYAN: FINAL COMPONENT-BY-COMPONENT VERIFICATION")
print("==============================================================")

# 1. System
temp = run("cat /sys/class/thermal/thermal_zone0/temp")
cpu_temp_c = float(temp)/1000.0 if temp else 0
uptime = run("uptime")
print(f"[1] SYSTEM SOC & KERNEL: Temp={cpu_temp_c:.1f}°C | {uptime}")

# 2. RKNPU & YOLO
ai_log = run("tail -n 1 /userdata/swachh_nayan/app.log")
print(f"[2] RKNPU & YOLOv5n: {ai_log}")

# 3. SC3336 Camera
try:
    r_cam = requests.get("http://172.32.0.93:8088/snapshot.bmp", timeout=2)
    print(f"[3] SC3336 CAMERA STREAM: HTTP {r_cam.status_code} ({len(r_cam.content)} bytes BMP)")
except Exception as e:
    print(f"[3] SC3336 CAMERA STREAM: Error {e}")

# 4. I2C3 Peripherals
i2c = run("i2cdetect -y 3")
has_lcd = "27" in i2c
has_adc = "48" in i2c
print(f"[4] I2C3 BUS: 0x27 (16x2 LCD)={'ONLINE' if has_lcd else 'OFFLINE'} | 0x48 (ADS1115 ADC)={'ONLINE' if has_adc else 'OFFLINE'}")

# 5. ADS1115 Voltage
ads_py = """
import sys; sys.path.insert(0, '/userdata/swachh_nayan_v2')
from hal.ads1115 import ADS1115
print(f'{ADS1115(i2c_bus=3, address=0x48).read_voltage(0):.4f}')
"""
v_ads = run(f"python3 -c \"{ads_py}\"")
print(f"[5] WATER LEVEL SENSOR (ADS1115 A0): {v_ads} V")

# 6. Pump Relay
r_on = requests.post("http://172.32.0.93:8088/api/set_motor", json={"state": "ON"}, timeout=2).json()
time.sleep(0.5)
g54_on = run("cat /sys/class/gpio/gpio54/value")
r_off = requests.post("http://172.32.0.93:8088/api/set_motor", json={"state": "OFF"}, timeout=2).json()
time.sleep(0.5)
g54_off = run("cat /sys/class/gpio/gpio54/value")
print(f"[6] 12V PUMP RELAY (GPIO 54): Set ON -> val={g54_on} | Set OFF -> val={g54_off}")

# 7. Servo Motor
pwm_duty_init = run("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
r_s90 = requests.post("http://172.32.0.93:8088/api/set_servo_angle", json={"angle": 90}, timeout=2).json()
time.sleep(0.5)
pwm_duty_90 = run("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
r_s0 = requests.post("http://172.32.0.93:8088/api/set_servo_angle", json={"angle": 0}, timeout=2).json()
time.sleep(0.5)
pwm_duty_0 = run("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
print(f"[7] SERVO MOTOR (PWM11): 90° duty={pwm_duty_90} ns | 0° duty={pwm_duty_0} ns")

# 8. Studio Dashboard HTML
r_dash = requests.get("http://172.32.0.93:8088/", timeout=2)
print(f"[8] STUDIO DASHBOARD: HTTP {r_dash.status_code} ({len(r_dash.text)} bytes) | Quick Bar present={'servo-quick-bar' in r_dash.text}")

c.close()
print("==============================================================")
print(" ALL CHECKS FINISHED.")
print("==============================================================")
