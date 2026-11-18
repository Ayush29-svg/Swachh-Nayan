import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run_cmd(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("1. Backing up swachh_nayan_app...")
run_cmd("cp -f /userdata/swachh_nayan/swachh_nayan_app /userdata/swachh_nayan/swachh_nayan_app.bak")

print("2. Killing existing swachh_nayan_app instances...")
run_cmd("killall -9 swachh_nayan_app 2>/dev/null || true")
time.sleep(1)

print("3. Patching string in swachh_nayan_app binary using Python on Pico...")
patch_script = """
import os

filepath = '/userdata/swachh_nayan/swachh_nayan_app'
with open(filepath, 'r+b') as f:
    data = f.read()
    target = b'/sys/class/pwm/pwmchip11/pwm0/duty_cycle'
    idx = data.find(target)
    print(f'Found target at offset: {hex(idx)}')
    if idx != -1:
        replacement = b'/tmp/pwm_app_dummy_sink' + b'\\x00' * (len(target) - len(b'/tmp/pwm_app_dummy_sink'))
        f.seek(idx)
        f.write(replacement)
        print('Patch applied successfully!')
    else:
        print('Target string not found or already patched.')
"""

run_cmd(f"python3 -c \"{patch_script}\"")

print("4. Testing if PWM duty cycle is stable...")
run_cmd("echo 1500000 > /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
time.sleep(0.5)
d1 = run_cmd("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
print(f"Duty right after set: {d1}")

for i in range(5):
    time.sleep(0.6)
    d = run_cmd("cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
    print(f"Duty after {(i+1)*0.6:.1f}s: {d}")

client.close()
