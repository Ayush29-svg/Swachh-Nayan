import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("==================================================")
print(" SWACHH-NAYAN: UNIVERSAL HARDWARE EXERCISER")
print("==================================================")

# 1. Export all candidate GPIOs
print("[1] Initializing GPIOs 54, 55, 56, 57, 58, 59...")
for p in [54, 55, 56, 57, 58, 59]:
    run(f"echo {p} > /sys/class/gpio/export 2>/dev/null || true")
    run(f"echo out > /sys/class/gpio/gpio{p}/direction 2>/dev/null || true")

# 2. Test Relay on GPIO 54, 57, 59 (Active-LOW: 0 = ON, 1 = OFF)
print("\n[2] Testing Relay with ACTIVE-LOW (0 = ON, 1 = OFF)...")
print("  --> Setting GPIO 54, 57, 59 to 0 (RELAY ON if Active-Low) for 3s...")
for p in [54, 57, 59]:
    run(f"echo 0 > /sys/class/gpio/gpio{p}/value")
time.sleep(3)

print("  --> Setting GPIO 54, 57, 59 to 1 (RELAY OFF if Active-Low) for 2s...")
for p in [54, 57, 59]:
    run(f"echo 1 > /sys/class/gpio/gpio{p}/value")
time.sleep(2)

# 3. Test Relay with ACTIVE-HIGH (1 = ON, 0 = OFF)
print("\n[3] Testing Relay with ACTIVE-HIGH (1 = ON, 0 = OFF)...")
print("  --> Setting GPIO 54, 57, 59 to 1 (RELAY ON if Active-High) for 3s...")
for p in [54, 57, 59]:
    run(f"echo 1 > /sys/class/gpio/gpio{p}/value")
time.sleep(3)

print("  --> Setting GPIO 54, 57, 59 to 0 (RELAY OFF if Active-High) for 2s...")
for p in [54, 57, 59]:
    run(f"echo 0 > /sys/class/gpio/gpio{p}/value")
time.sleep(1)

# 4. Test Servo: Hardware PWM11 on Pin 4
print("\n[4] Testing Servo via Hardware PWM11 (Pin 4)...")
run("echo 55 > /sys/class/gpio/unexport 2>/dev/null || true")
run("echo 0 > /sys/class/pwm/pwmchip11/export 2>/dev/null || true")
run("echo 20000000 > /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null || true")
run("echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null || true")

for duty in [1000000, 1500000, 2000000, 1000000]:
    print(f"  --> Hardware PWM11 duty: {duty} ns...")
    run(f"echo {duty} > /sys/class/pwm/pwmchip11/pwm0/duty_cycle")
    time.sleep(1)

# 5. Test Servo: Bit-bang PWM on GPIO 56 (Pin 35 as per visual assembly guide)
print("\n[5] Testing Servo via Bit-Bang PWM on GPIO 56 (Pin 35)...")
run("echo 56 > /sys/class/gpio/export 2>/dev/null || true")
run("echo out > /sys/class/gpio/gpio56/direction 2>/dev/null || true")

# Bit-bang 50 pulses at 1.5ms (90 deg) and 50 pulses at 2.0ms (180 deg) on GPIO 56
bitbang_script = """
import time
import os

def pulse(pin, high_s, count=50):
    val_path = f'/sys/class/gpio/gpio{pin}/value'
    with open(val_path, 'w') as f:
        for _ in range(count):
            f.write('1\\n')
            f.flush()
            time.sleep(high_s)
            f.write('0\\n')
            f.flush()
            time.sleep(max(0.001, 0.020 - high_s))

print('Pulsing GPIO 56 at 1.5ms (90 deg)...')
pulse(56, 0.0015, 60)
time.sleep(0.5)
print('Pulsing GPIO 56 at 2.0ms (180 deg)...')
pulse(56, 0.0020, 60)
time.sleep(0.5)
print('Pulsing GPIO 56 at 1.0ms (0 deg)...')
pulse(56, 0.0010, 60)
"""
client.exec_command(f"python3 -c \"{bitbang_script}\"")
time.sleep(5)

print("\n[6] Universal Hardware Exerciser Finished.")
client.close()
