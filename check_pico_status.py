import paramiko
import time

time.sleep(2)
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

cmds = [
    "ps | grep swachh",
    "netstat -tulnp",
    "curl -I http://127.0.0.1:8080/ || echo 'no 8080'",
    "curl -I http://127.0.0.1:8088/ || echo 'no 8088'"
]

for cmd in cmds:
    stdin, stdout, stderr = client.exec_command(cmd)
    print(f"=== {cmd} ===")
    out = stdout.read().decode().strip()
    if out: print(out)

client.close()
