import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("1. Disabling PWM on Pin 4...")
run("echo 0 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null || true")

print("2. Exporting Pin 4 as GPIO 55...")
run("echo 55 > /sys/class/gpio/export 2>/dev/null || true")
run("echo out > /sys/class/gpio/gpio55/direction 2>/dev/null || true")

print("3. Setting Pin 4 to HIGH (Constant 3.3V)...")
run("echo 1 > /sys/class/gpio/gpio55/value")

val = run("cat /sys/class/gpio/gpio55/value")
print(f"Pin 4 GPIO55 state: {val} (Should read +3.3V on multimeter)")

client.close()
