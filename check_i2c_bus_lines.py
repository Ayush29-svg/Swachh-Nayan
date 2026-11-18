import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("--- Checking Pin 9 (SDA) and Pin 10 (SCL) GPIO levels ---")
# GPIO 58 = Pin 9 (SDA)
# GPIO 59 = Pin 10 (SCL)
run("echo 58 > /sys/class/gpio/export 2>/dev/null || true")
run("echo 59 > /sys/class/gpio/export 2>/dev/null || true")
run("echo in > /sys/class/gpio/gpio58/direction 2>/dev/null || true")
run("echo in > /sys/class/gpio/gpio59/direction 2>/dev/null || true")

val_sda = run("cat /sys/class/gpio/gpio58/value 2>/dev/null")
val_scl = run("cat /sys/class/gpio/gpio59/value 2>/dev/null")

print(f"Pin 9  (SDA / GPIO58): {val_sda} (1=HIGH, 0=STUCK LOW / GROUND)")
print(f"Pin 10 (SCL / GPIO59): {val_scl} (1=HIGH, 0=STUCK LOW / GROUND)")

# Unexport so I2C controller can use them again
run("echo 58 > /sys/class/gpio/unexport 2>/dev/null || true")
run("echo 59 > /sys/class/gpio/unexport 2>/dev/null || true")

client.close()
