import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

cmds = [
    "python3 --version || python --version",
    "which rknn_server || echo 'no rknn_server'",
    "which rknpu || echo 'no rknpu'",
    "df -h",
    "free -m",
    "python3 -c 'import cv2; print(cv2.__version__)' 2>&1"
]

for cmd in cmds:
    stdin, stdout, stderr = client.exec_command(cmd)
    print(f"=== {cmd} ===")
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out: print(out)
    if err: print("ERR:", err)

client.close()
