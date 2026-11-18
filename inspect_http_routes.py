import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

stdin, stdout, stderr = client.exec_command("strings /userdata/swachh_nayan/swachh_nayan_app | grep -E 'GET |POST |HTTP/|/api' -C 3")
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
