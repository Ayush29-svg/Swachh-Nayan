import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("================================================================")
print(" SWACHH-NAYAN: SERVO MULTI-PIN HARDWARE SIGNAL SCANNER")
print(" Watch your physical servo motor horn during each phase below!  ")
print("================================================================")

# PHASE 1: Physical Pin 4 (Rockchip Hardware PWM11)
print("\n[PHASE 1] Testing Physical Pin 4 (Hardware PWM11)...")
print("  --> Ensuring Pin 4 is in PWM mode (unexporting gpio55)...")
run("echo 55 > /sys/class/gpio/unexport 2>/dev/null || true")
run("echo 0 > /sys/class/pwm/pwmchip11/export 2>/dev/null || true")
run("echo 20000000 > /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null || true")
run("echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null || true")

for angle, duty in [(0, 1000000), (90, 1500000), (180, 2000000), (0, 1000000)]:
    print(f"  --> Pin 4 (PWM11): Actuating to {angle}° (Duty: {duty} ns)...")
    run(f"echo {duty} > /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
    time.sleep(1.5)

# PHASE 2: Physical Pin 35 (GPIO 56 - as per Assembly Guide)
print("\n[PHASE 2] Testing Physical Pin 35 (GPIO 56)...")
run("echo 56 > /sys/class/gpio/export 2>/dev/null || true")
run("echo out > /sys/class/gpio/gpio56/direction 2>/dev/null || true")

script_pin35 = """
import time
val_path = '/sys/class/gpio/gpio56/value'
for angle, high_s in [(0, 0.0010), (90, 0.0015), (180, 0.0020), (0, 0.0010)]:
    print(f'  --> Pin 35 (GPIO56): Sending 60 pulses for {angle}° ({high_s*1000:.1f}ms)...')
    with open(val_path, 'w') as f:
        for _ in range(60):
            f.write('1\\n')
            f.flush()
            time.sleep(high_s)
            f.write('0\\n')
            f.flush()
            time.sleep(max(0.001, 0.020 - high_s))
    time.sleep(0.5)
"""
stdin, stdout, stderr = client.exec_command(f"python3 -c \"{script_pin35}\"")
print(stdout.read().decode())

# PHASE 3: Physical Pin 4 via Software GPIO55 bit-banging
print("\n[PHASE 3] Testing Physical Pin 4 via Software GPIO55 bit-banging...")
run("echo 0 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null || true")
run("echo 55 > /sys/class/gpio/export 2>/dev/null || true")
run("echo out > /sys/class/gpio/gpio55/direction 2>/dev/null || true")

script_pin4_gpio = """
import time
val_path = '/sys/class/gpio/gpio55/value'
for angle, high_s in [(0, 0.0010), (90, 0.0015), (180, 0.0020), (0, 0.0010)]:
    print(f'  --> Pin 4 (GPIO55 bit-bang): Sending 60 pulses for {angle}° ({high_s*1000:.1f}ms)...')
    with open(val_path, 'w') as f:
        for _ in range(60):
            f.write('1\\n')
            f.flush()
            time.sleep(high_s)
            f.write('0\\n')
            f.flush()
            time.sleep(max(0.001, 0.020 - high_s))
    time.sleep(0.5)
"""
stdin, stdout, stderr = client.exec_command(f"python3 -c \"{script_pin4_gpio}\"")
print(stdout.read().decode())

# Restore PWM mode on Pin 4
run("echo 55 > /sys/class/gpio/unexport 2>/dev/null || true")
run("echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null || true")

print("================================================================")
print(" Servo multi-pin scan complete.")
print("================================================================")
client.close()
