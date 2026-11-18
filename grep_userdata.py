import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.32.0.93', username='root', password='luckfox', timeout=5)

for pattern in ['1800000', 'duty_cycle']:
    print(f"=== GREP FOR {pattern} ===")
    stdin, stdout, stderr = client.exec_command(f"grep -rn '{pattern}' /userdata/swachh_nayan_v2/ 2>/dev/null")
    print(stdout.read().decode('utf-8', errors='replace').encode('ascii', errors='replace').decode())

client.close()
