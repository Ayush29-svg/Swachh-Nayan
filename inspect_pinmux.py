import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

cmds = [
    "cat /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-pins 2>/dev/null | grep -E 'gpio1c7|pwm11|gpio55|pin 55' || true",
    "grep -rn 'pwm11' /sys/ 2>/dev/null | head -n 20",
    "luckfox-config info 2>/dev/null || true",
    "cat /etc/luckfox.cfg 2>/dev/null || true"
]

for cmd in cmds:
    print(f"=== {cmd} ===")
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace').strip())

client.close()
