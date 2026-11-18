import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

cmds = [
    "ls -la /userdata",
    "ls -la /oem/usr/bin",
    "which rkaiq_3A_server || echo 'no rkaiq'",
    "which luckfox || echo 'no luckfox'",
    "find /oem /userdata /usr -name '*v4l2*' -o -name '*camera*' -o -name '*rkaiq*' -o -name '*luckfox*' 2>/dev/null",
    "ls -l /sys/class/pwm"
]

for cmd in cmds:
    stdin, stdout, stderr = client.exec_command(cmd)
    print(f"=== {cmd} ===")
    out = stdout.read().decode().strip()
    if out: print(out)

client.close()
