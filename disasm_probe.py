import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

stdin, stdout, stderr = client.exec_command('objdump -d /userdata/swachh_nayan/hw_probe_all | grep -C 20 "main>" | head -n 45')
print(stdout.read().decode('utf-8', errors='replace'))

stdin, stdout, stderr = client.exec_command('objdump -d /userdata/swachh_nayan/hw_probe_all | grep -A 80 "<main>:"')
print(stdout.read().decode('utf-8', errors='replace'))

client.close()
