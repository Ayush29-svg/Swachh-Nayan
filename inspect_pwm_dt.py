import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

cmds = [
    "grep -rn 'pwm11' /sys/firmware/devicetree/ 2>/dev/null",
    "cat /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinconf-pins 2>/dev/null | grep -E 'gpio1_c7|gpio1_c0|pwm' | head -n 30 || true",
    "dmesg | grep -i pwm",
    "cat /sys/class/pwm/pwmchip11/device/uevent 2>/dev/null"
]

for cmd in cmds:
    print(f"=== {cmd} ===")
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace').strip())

client.close()
