import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

stdin, stdout, stderr = client.exec_command('find /userdata/ -name "*.cpp" -o -name "*.c" -o -name "*.h"')
print('Files on Luckfox:')
print(stdout.read().decode())

stdin, stdout, stderr = client.exec_command('ls -la /userdata/swachh_nayan/')
print('Contents of /userdata/swachh_nayan/:')
print(stdout.read().decode())

client.close()
