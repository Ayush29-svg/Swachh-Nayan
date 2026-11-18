import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

cmds = [
    "curl -I http://127.0.0.1:8080/ || echo 'curl failed'",
    "curl -I http://127.0.0.1:8080/snapshot.bmp || echo 'curl snapshot failed'",
    "ps -o pid,comm,args -p 840",
    "cat /userdata/swachh_nayan/rkaiq.log 2>/dev/null | tail -n 25"
]

for cmd in cmds:
    stdin, stdout, stderr = client.exec_command(cmd)
    print(f"=== {cmd} ===")
    out = stdout.read().decode().strip()
    if out: print(out)

client.close()
