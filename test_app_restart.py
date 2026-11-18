import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run_cmd(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("1. Starting swachh_nayan_app in background...")
client.exec_command("cd /userdata/swachh_nayan && export LD_LIBRARY_PATH=/userdata/swachh_nayan/lib && nohup ./swachh_nayan_app model/yolov5n_rv1103.rknn >> app.log 2>&1 &")
time.sleep(3)

print("2. Checking process list:")
print(run_cmd("ps | grep swachh_nayan_app"))

print("3. Checking app.log tail:")
print(run_cmd("tail -n 20 /userdata/swachh_nayan/app.log"))

print("4. Checking if PWM duty cycle is affected by swachh_nayan_app:")
run_cmd("echo 1250000 > /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
time.sleep(0.5)
print("Duty right after setting 1250000:", run_cmd("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle"))
time.sleep(1.5)
print("Duty after 1.5s:", run_cmd("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle"))

client.close()
