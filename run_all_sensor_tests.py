import paramiko
import time
import json
import urllib.request

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = c.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("=================================================================")
print("     SWACHH-NAYAN: COMPLETE SENSOR & ACTUATOR TEST RUN           ")
print("=================================================================")

# 1. System Health
print("\n[1/7] SYSTEM SOC & COMPUTE:")
uptime = run("uptime")
cpu_temp_raw = run("cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null")
cpu_temp_c = f"{float(cpu_temp_raw)/1000.0:.1f}°C" if cpu_temp_raw else "N/A"
mem = run("free -m | grep Mem")
npu_dev = run("ls -l /dev/rknpu 2>/dev/null")
print(f"  • Uptime: {uptime}")
print(f"  • SoC Core Temperature: {cpu_temp_c}")
print(f"  • RAM Utilization: {mem}")
print(f"  • RKNPU Driver: {'ONLINE' if npu_dev else 'OFFLINE'}")

# 2. Camera & Vision Process
print("\n[2/7] SC3336 3MP MIPI CAMERA & YOLOv5n AI VISION:")
ps_app = run("ps | grep swachh_nayan_app | grep -v grep")
print(f"  • AI Process: {ps_app if ps_app else 'OFFLINE'}")
recent_log = run("tail -n 2 /userdata/swachh_nayan/app.log 2>/dev/null")
print(f"  • AI Log:\n    {recent_log}")

# 3. I2C3 Bus Scan
print("\n[3/7] I2C3 PERIPHERAL SCAN (/dev/i2c-3):")
i2c_matrix = run("i2cdetect -y 3 2>/dev/null")
print(f"  • Detected nodes on I2C3:\n{i2c_matrix}")

# 4. LCD1602 Test
print("\n[4/7] 16x2 I2C CHARACTER LCD TEST (0x27):")
lcd_code = """
import sys
sys.path.insert(0, '/userdata/swachh_nayan_v2')
try:
    from hal.lcd1602 import LCD1602
    lcd = LCD1602(i2c_bus=3, address=0x27)
    lcd.write_string('SWACHH-NAYAN OK ', 0)
    lcd.write_string('TEST RUN ACTIVE ', 1)
    print('  [LCD SUCCESS] Display text written: \"SWACHH-NAYAN OK / TEST RUN ACTIVE\"')
except Exception as e:
    print('  [LCD ERROR]:', e)
"""
print(run(f"python3 -c \"{lcd_code}\""))

# 5. ADS1115 Water Level Sensor Test
print("\n[5/7] ADS1115 16-BIT ADC WATER SENSOR TEST (0x48):")
ads_code = """
import sys
sys.path.insert(0, '/userdata/swachh_nayan_v2')
try:
    from hal.ads1115 import ADS1115
    ads = ADS1115(i2c_bus=3, address=0x48)
    v0 = ads.read_voltage(0)
    pct = max(0.0, min(100.0, (v0 / 3.0) * 100.0))
    print(f'  [ADC SUCCESS] Channel A0 Voltage: {v0:.4f} V | Water Level: {pct:.1f}%')
except Exception as e:
    print('  [ADC ERROR]:', e)
"""
print(run(f"python3 -c \"{ads_code}\""))

# 6. 12V Water Pump Relay Test
print("\n[6/7] 12V WATER PUMP RELAY TEST (PIN 5 / GPIO 54):")
run("echo 54 > /sys/class/gpio/export 2>/dev/null || true")
run("echo out > /sys/class/gpio/gpio54/direction 2>/dev/null || true")
print("  • Triggering Relay ON (Listen for audible CLICK & check red LED)...")
run("echo 1 > /sys/class/gpio/gpio54/value")
time.sleep(2.0)
print("  • Triggering Relay OFF...")
run("echo 0 > /sys/class/gpio/gpio54/value")
print("  [RELAY TEST COMPLETE]")

# 7. MG996R Servo Flap Actuation Test
print("\n[7/7] MG996R SERVO DIVERSION FLAP ACTUATION TEST:")
run("echo 55 > /sys/class/gpio/unexport 2>/dev/null || true")
run("echo 0 > /sys/class/pwm/pwmchip11/export 2>/dev/null || true")
run("echo 20000000 > /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null || true")
run("echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null || true")

for g in [48, 54]:
    run(f"echo {g} > /sys/class/gpio/export 2>/dev/null || true")
    run(f"echo out > /sys/class/gpio/gpio{g}/direction 2>/dev/null || true")

servo_code = """
import time

pwm_duty = '/sys/class/pwm/pwmchip11/pwm0/duty_cycle'
gpio_paths = ['/sys/class/gpio/gpio48/value', '/sys/class/gpio/gpio54/value']

positions = [
    ('0° (REST / NORMAL FLOW)', 1000000, 0.0010, 2.0),
    ('90° (DIVERSION GATE OPEN)', 1500000, 0.0015, 2.5),
    ('180° (MAXIMUM DEFLECTION)', 2000000, 0.0020, 2.0),
    ('0° (RETURN TO REST)', 1000000, 0.0010, 2.0)
]

for label, duty, high_s, hold_sec in positions:
    print(f'  >> Moving to {label} | Duty: {duty} ns...', flush=True)
    try:
        with open(pwm_duty, 'w') as f:
            f.write(f'{duty}\\n')
    except Exception:
        pass
    
    open_fds = []
    for p in gpio_paths:
        try:
            open_fds.append(open(p, 'w'))
        except Exception:
            pass
    for _ in range(int(hold_sec / 0.020)):
        for fd in open_fds:
            fd.write('1\\n')
            fd.flush()
        time.sleep(high_s)
        for fd in open_fds:
            fd.write('0\\n')
            fd.flush()
        time.sleep(max(0.001, 0.020 - high_s))
    for fd in open_fds:
        fd.close()

print('  [SERVO TEST COMPLETE]')
"""
print(run(f"python3 -c \"{servo_code}\""))

# Ensure server_live.py is running for the web dashboard
ps_srv = run("ps | grep server_live.py | grep -v grep")
if not ps_srv:
    print("\n[DAEMON] Starting server_live.py dashboard on port 8088...")
    run("nohup python3 -u /userdata/swachh_nayan_v2/server_live.py >> /userdata/swachh_nayan_v2/server_live.log 2>&1 &")
    time.sleep(1)

c.close()
print("\n=================================================================")
print("           ALL SENSOR & ACTUATOR TESTS COMPLETED                 ")
print("=================================================================")
