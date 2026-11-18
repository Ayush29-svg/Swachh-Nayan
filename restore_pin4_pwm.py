import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("Unexporting GPIO 55...")
run("echo 55 > /sys/class/gpio/unexport 2>/dev/null || true")

print("Enabling Hardware PWM11 on Pin 4...")
run("echo 0 > /sys/class/pwm/pwmchip11/export 2>/dev/null || true")
run("echo 20000000 > /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null || true")
run("echo 1500000 > /sys/class/pwm/pwmchip11/pwm0/duty_cycle 2>/dev/null || true")
run("echo 1 > /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null || true")

print("Pin 4 restored to 50Hz PWM mode (1.5ms pulse)!")
client.close()
