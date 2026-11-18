import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

cmds = [
    "find /usr/lib /userdata -name '*cv2*' 2>/dev/null",
    "python3 -c 'import sys; print(sys.path)'",
    "pip3 list || pip list || echo 'no pip'",
    "which v4l2-ctl && v4l2-ctl --list-devices",
    "v4l2-ctl -d /dev/video11 --all 2>&1 | head -n 30"
]

for cmd in cmds:
    stdin, stdout, stderr = client.exec_command(cmd)
    print(f"=== {cmd} ===")
    out = stdout.read().decode().strip()
    if out: print(out)

client.close()
