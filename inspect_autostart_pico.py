import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

cmds = [
    "cat /etc/init.d/S* | grep -E 'swachh|python'",
    "ls -la /etc/init.d/",
    "cat /userdata/swachh_nayan/run*.sh 2>/dev/null",
    "cat /etc/profile 2>/dev/null",
    "cat /etc/rc.local 2>/dev/null"
]

for cmd in cmds:
    print(f"=== {cmd} ===")
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace').strip())

client.close()
