import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

stdin, stdout, stderr = client.exec_command("strings -t d /userdata/swachh_nayan/hw_probe_all | grep -C 3 'TESTING'")
print(stdout.read().decode('utf-8', errors='replace'))

client.close()
