import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

stdin, stdout, stderr = client.exec_command("grep -n 'def do_POST' -A 70 /userdata/swachh_nayan_v2/server_live.py")
print(stdout.read().decode())
client.close()
