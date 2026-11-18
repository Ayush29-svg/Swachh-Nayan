import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

# Search for gpio 54 in the binary or disassembly
stdin, stdout, stderr = client.exec_command("objdump -d /userdata/swachh_nayan/swachh_nayan_app 2>/dev/null | grep -C 10 toggle_pump || strings -t d /userdata/swachh_nayan/swachh_nayan_app | grep -C 5 54")
print("Output:")
print(stdout.read().decode('utf-8', errors='replace'))

client.close()
