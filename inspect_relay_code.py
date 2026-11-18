import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

stdin, stdout, stderr = client.exec_command("grep -n -C 10 -i 'gpio54' /userdata/swachh_nayan_v2/server_live.py")
output = stdout.read().decode('utf-8', errors='replace')
print("GPIO54 in server_live.py:")
print(output)

stdin, stdout, stderr = client.exec_command("grep -n -C 10 -i 'relay' /userdata/swachh_nayan_v2/server_live.py")
output = stdout.read().decode('utf-8', errors='replace')
with open("relay_in_server.txt", "w", encoding="utf-8") as f:
    f.write(output)
print("Relay grep output length:", len(output))
client.close()
