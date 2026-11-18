import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

stdin, stdout, stderr = client.exec_command("find /userdata -name '*.cpp' -o -name '*.c' -o -name 'CMakeLists.txt' -o -name 'Makefile' 2>/dev/null")
print(stdout.read().decode('utf-8', errors='replace'))
client.close()
