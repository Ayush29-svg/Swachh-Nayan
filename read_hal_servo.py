import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

stdin, stdout, stderr = client.exec_command('cat /userdata/swachh_nayan_v2/hal/servo.py')
print(stdout.read().decode('utf-8', errors='replace').encode('ascii', errors='replace').decode())

client.close()
