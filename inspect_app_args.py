import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

stdin, stdout, stderr = client.exec_command("cd /userdata/swachh_nayan && ./swachh_nayan_app --help || ./swachh_nayan_app -h")
print("Help output:")
print(stdout.read().decode('utf-8', errors='replace'))
print("Error output:")
print(stderr.read().decode('utf-8', errors='replace'))

client.close()
