import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

cmds = [
    "strings /userdata/swachh_nayan/swachh_nayan_app | grep -E 'pwm|gpio|relay' | head -n 30",
    "cat /sys/class/pwm/pwmchip11/pwm0/enable 2>/dev/null",
    "cat /sys/class/pwm/pwmchip11/pwm0/period 2>/dev/null",
    "cat /sys/class/pwm/pwmchip11/pwm0/duty_cycle 2>/dev/null",
    "cat /sys/class/gpio/gpio54/value 2>/dev/null",
    "cat /sys/class/gpio/gpio54/direction 2>/dev/null"
]

for cmd in cmds:
    print(f"=== {cmd} ===")
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace'))

client.close()
