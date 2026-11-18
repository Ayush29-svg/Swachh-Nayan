import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

stdin, stdout, stderr = client.exec_command("grep -n -C 5 -i 'pump' /userdata/swachh_nayan_v2/server_live.py")
output = stdout.read().decode('utf-8', errors='replace')
with open("pump_grep_output.txt", "w", encoding="utf-8") as f:
    f.write(output)
print("Output written to pump_grep_output.txt, length:", len(output))
client.close()
