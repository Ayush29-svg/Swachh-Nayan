import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

cmds = [
    "netstat -tulnp",
    "tail -n 35 /userdata/swachh_nayan_v2/server_live.log",
    "head -n 40 /userdata/swachh_nayan_v2/server_live.py"
]

for cmd in cmds:
    stdin, stdout, stderr = client.exec_command(cmd)
    print(f"=== {cmd} ===")
    out = stdout.read().decode().strip()
    if out: print(out)

client.close()
