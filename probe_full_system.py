import paramiko
import time
import json
import urllib.request

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def exec_cmd(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("=================================================================")
print("     SWACHH-NAYAN: COMPREHENSIVE ALL-COMPONENT HEALTH AUDIT      ")
print("=================================================================")

# 1. CORE COMPUTE & RKNPU
print("\n[1/7] COMPUTE & RKNPU NPU ACCELERATOR:")
uptime = exec_cmd("uptime")
cpu_temp = exec_cmd("cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null")
temp_c = f"{float(cpu_temp)/1000.0:.1f}°C" if cpu_temp else "N/A"
mem = exec_cmd("free -m | grep Mem")
npu_dev = exec_cmd("ls -l /dev/rknpu 2>/dev/null")
print(f"  • Uptime: {uptime}")
print(f"  • Core SoC Temp: {temp_c}")
print(f"  • Memory (MB): {mem}")
print(f"  • /dev/rknpu device node: {'ONLINE (' + npu_dev + ')' if npu_dev else 'OFFLINE'}")

# 2. SC3336 3MP MIPI CSI CAMERA
print("\n[2/7] SC3336 MIPI CSI CAMERA SENSOR & ISP:")
cam_nodes = exec_cmd("ls -l /dev/video* 2>/dev/null")
subdevs = exec_cmd("ls -l /dev/v4l-subdev* 2>/dev/null")
rkaiq = exec_cmd("ps | grep -v grep | grep rkaiq_3A_server")
print(f"  • Video nodes: {len(cam_nodes.splitlines())} detected")
print(f"  • V4L2 subdevs: {len(subdevs.splitlines())} detected (/dev/v4l-subdev2 is SC3336)")
print(f"  • Rockchip AIQ 3A ISP Server: {'RUNNING' if rkaiq else 'STOPPED'}")

# 3. NPU AI VISION & CAPTURE PROCESS (PORT 8080)
print("\n[3/7] NPU AI VISION PROCESS (swachh_nayan_app):")
app_ps = exec_cmd("ps | grep -v grep | grep swachh_nayan_app")
print(f"  • Process: {app_ps if app_ps else 'NOT RUNNING'}")
app_log = exec_cmd("tail -n 5 /userdata/swachh_nayan/app.log 2>/dev/null")
print(f"  • Recent AI log:\n{app_log}")

# 4. 12V DC WATER PUMP RELAY (GPIO 54 / PIN 5)
print("\n[4/7] 12V DC PUMP RELAY (PIN 5 / GPIO 54):")
gpio54_val = exec_cmd("cat /sys/class/gpio/gpio54/value 2>/dev/null")
gpio54_dir = exec_cmd("cat /sys/class/gpio/gpio54/direction 2>/dev/null")
print(f"  • GPIO54 direction: {gpio54_dir}, value: {gpio54_val}")
print("  • Physical Relay: Coil & LED trigger verified working by user.")

# 5. I2C PERIPHERALS: ADS1115 (0x48) & 16x2 LCD (0x27)
print("\n[5/7] I2C3 BUS SCAN (/dev/i2c-3):")
i2c_scan = exec_cmd("i2cdetect -y 3 2>/dev/null || echo 'i2cdetect not installed'")
print(f"  • I2C3 Matrix:\n{i2c_scan}")

# 6. HC-SR04 ULTRASONIC SENSOR
print("\n[6/7] HC-SR04 ULTRASONIC SENSOR:")
trig_val = exec_cmd("cat /sys/class/gpio/gpio53/value 2>/dev/null || cat /sys/class/gpio/gpio57/value 2>/dev/null")
echo_val = exec_cmd("cat /sys/class/gpio/gpio52/value 2>/dev/null || cat /sys/class/gpio/gpio58/value 2>/dev/null")
print(f"  • Trig line: {trig_val}, Echo line: {echo_val}")

# 7. MG996R SERVO MOTOR - DETAILED PIN & PWM AUDIT
print("\n[7/7] MG996R SERVO MOTOR - HARDWARE PWM & GPIO NODES:")
pwm_chip = exec_cmd("ls -d /sys/class/pwm/pwmchip* 2>/dev/null")
pwm_node = exec_cmd("ls -d /sys/class/pwm/pwmchip11/pwm0 2>/dev/null")
pwm_enable = exec_cmd("cat /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null")
pwm_period = exec_cmd("cat /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null")
pwm_duty = exec_cmd("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle 2>/dev/null")
gpio55_exp = exec_cmd("ls -d /sys/class/gpio/gpio55 2>/dev/null || echo 'NOT EXPORTED'")
gpio56_exp = exec_cmd("ls -d /sys/class/gpio/gpio56 2>/dev/null || echo 'NOT EXPORTED'")

print(f"  • PWM Chips: {pwm_chip}")
print(f"  • PWM0 Node: {pwm_node}")
print(f"  • PWM Period: {pwm_period} ns ({float(pwm_period)/1e6:.1f} ms -> {1e9/float(pwm_period):.1f} Hz)" if pwm_period else "  • PWM Period: NOT SET")
print(f"  • PWM Duty: {pwm_duty} ns ({float(pwm_duty)/1e6:.3f} ms)" if pwm_duty else "  • PWM Duty: NOT SET")
print(f"  • PWM Enable: {pwm_enable}")
print(f"  • Pin 4 (GPIO55) pinmux conflict status: {gpio55_exp}")
print(f"  • Pin 35 (GPIO56) status: {gpio56_exp}")

client.close()
print("\n=================================================================")
print("                   END OF COMPONENT AUDIT                        ")
print("=================================================================")
