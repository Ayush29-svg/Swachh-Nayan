import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("Mounting debugfs...")
run("mount -t debugfs none /sys/kernel/debug 2>/dev/null || true")

print("Checking pinctrl directories:")
print(run("ls /sys/kernel/debug/pinctrl/"))

print("Checking pinmux-pins for PWM11 / GPIO55:")
print(run("cat /sys/kernel/debug/pinctrl/*/pinmux-pins 2>/dev/null | grep -E 'pin 55|pwm11|gpio1-23' || true"))

print("Checking pinmux-functions:")
print(run("cat /sys/kernel/debug/pinctrl/*/pinmux-functions 2>/dev/null | grep -E 'pwm' || true"))

client.close()
